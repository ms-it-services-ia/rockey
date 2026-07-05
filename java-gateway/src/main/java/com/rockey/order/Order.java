package com.rockey.order;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "orders")
public class Order {

    @Id private String id;

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "client_email")
    private String clientEmail;

    @Column(name = "client_name")
    private String clientName;

    @Column(name = "article_id")
    private String articleId;

    private BigDecimal amount;

    private String status;

    @Column(name = "order_date")
    private LocalDate orderDate;

    @Column(name = "delivery_date")
    private LocalDate deliveryDate;

    protected Order() {}

    public String getId() {
        return id;
    }

    public String getTenantId() {
        return tenantId;
    }

    public String getClientEmail() {
        return clientEmail;
    }

    public String getClientName() {
        return clientName;
    }

    public String getArticleId() {
        return articleId;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public String getStatus() {
        return status;
    }

    public LocalDate getOrderDate() {
        return orderDate;
    }

    public LocalDate getDeliveryDate() {
        return deliveryDate;
    }
}
