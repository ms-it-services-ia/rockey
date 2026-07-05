package com.rockey.eligibility;

import com.rockey.order.Order;
import com.rockey.order.OrderRepository;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.NoSuchElementException;
import org.springframework.stereotype.Service;

/**
 * Applies the retailer's policy thresholds mechanically (constitution III.1 — Java executes,
 * it never exercises judgment beyond comparing against the numbers PolicyLoader gives it;
 * constitution V.3 — decision based only on policy + thresholds, never LLM intuition).
 */
@Service
public class EligibilityService {

    private final OrderRepository orderRepository;
    private final PolicyLoader policyLoader;

    public EligibilityService(OrderRepository orderRepository, PolicyLoader policyLoader) {
        this.orderRepository = orderRepository;
        this.policyLoader = policyLoader;
    }

    public record ArticleEligibilityInput(boolean returnable, String nonReturnReason) {}

    public record EligibilityResult(
            boolean eligible, boolean autoApprovable, String reason, String appliedRule) {}

    public EligibilityResult checkReturnEligibility(
            String tenantId, String orderId, ArticleEligibilityInput article, boolean isInternational) {
        Order order =
                orderRepository
                        .findByIdAndTenantId(orderId, tenantId)
                        .orElseThrow(() -> new NoSuchElementException("Order not found: " + orderId));

        PolicyThresholds thresholds = policyLoader.load(tenantId);

        if (!article.returnable()) {
            return new EligibilityResult(
                    false,
                    false,
                    "Item excluded from returns: " + article.nonReturnReason(),
                    "non_returnable_article_type:" + article.nonReturnReason());
        }

        int windowDays =
                isInternational
                        ? thresholds.returnWindowDaysInternational()
                        : thresholds.returnWindowDaysDomestic();
        LocalDate deadline = order.getDeliveryDate().plusDays(windowDays);
        if (LocalDate.now().isAfter(deadline)) {
            return new EligibilityResult(
                    false, false, "Return window exceeded", "return_window:" + windowDays + "d");
        }

        BigDecimal amount = order.getAmount();
        boolean autoApprovable = amount.compareTo(thresholds.autoRefundMaxAmount()) <= 0;
        String appliedRule =
                autoApprovable
                        ? "auto_refund_threshold:" + thresholds.autoRefundMaxAmount()
                        : "manual_review_threshold:" + thresholds.manualReviewMaxAmount();

        return new EligibilityResult(true, autoApprovable, "Eligible for return", appliedRule);
    }

    public record ComplaintEligibilityResult(
            boolean eligible, boolean requiresEscalation, String reason, String appliedRule) {}

    /**
     * Complaint-specific rules (spec User Story 5, T067): unlike a change-of-mind return, a
     * quality complaint isn't blocked by the article's normal returnability — a defective
     * "unique piece" is still a valid complaint. Within the standard return window, a
     * complaint resolves the same way a return would (auto vs. manual, by amount). Past the
     * return window but within the legal warranty period, the complaint is still eligible
     * but MUST escalate with a note (constitution never lets the agent silently apply a
     * looser rule on its own judgment). Past the legal warranty entirely, it's refused.
     */
    public ComplaintEligibilityResult checkComplaintEligibility(
            String tenantId, String orderId, boolean isInternational) {
        Order order =
                orderRepository
                        .findByIdAndTenantId(orderId, tenantId)
                        .orElseThrow(() -> new NoSuchElementException("Order not found: " + orderId));

        PolicyThresholds thresholds = policyLoader.load(tenantId);

        int windowDays =
                isInternational
                        ? thresholds.returnWindowDaysInternational()
                        : thresholds.returnWindowDaysDomestic();
        LocalDate returnDeadline = order.getDeliveryDate().plusDays(windowDays);
        LocalDate legalWarrantyDeadline = order.getDeliveryDate().plusDays(thresholds.legalWarrantyDays());
        LocalDate today = LocalDate.now();

        if (today.isAfter(legalWarrantyDeadline)) {
            return new ComplaintEligibilityResult(
                    false, false, "Legal warranty period expired", "legal_warranty:" + thresholds.legalWarrantyDays() + "d");
        }

        if (today.isAfter(returnDeadline)) {
            return new ComplaintEligibilityResult(
                    true,
                    true,
                    "Past the standard return window — legal warranty applies",
                    "legal_warranty:" + thresholds.legalWarrantyDays() + "d");
        }

        BigDecimal amount = order.getAmount();
        boolean autoApprovable = amount.compareTo(thresholds.autoRefundMaxAmount()) <= 0;
        String appliedRule =
                autoApprovable
                        ? "auto_refund_threshold:" + thresholds.autoRefundMaxAmount()
                        : "manual_review_threshold:" + thresholds.manualReviewMaxAmount();

        return new ComplaintEligibilityResult(true, !autoApprovable, "Eligible complaint", appliedRule);
    }
}
