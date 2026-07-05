package com.rockey.eligibility;

import java.math.BigDecimal;

public record PolicyThresholds(
        int returnWindowDaysDomestic,
        int returnWindowDaysInternational,
        BigDecimal autoRefundMaxAmount,
        BigDecimal manualReviewMaxAmount,
        int legalWarrantyDays) {}
