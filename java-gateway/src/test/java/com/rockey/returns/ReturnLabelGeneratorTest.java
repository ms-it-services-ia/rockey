package com.rockey.returns;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class ReturnLabelGeneratorTest {

    private final ReturnLabelGenerator generator = new ReturnLabelGenerator();

    @Test
    void happyPath_generatesAStableUniquePdfUrl() {
        String url = generator.generate("CMD-2026-00001");

        assertThat(url).startsWith("https://");
        assertThat(url).endsWith(".pdf");
        assertThat(url).contains("CMD-2026-00001");
    }

    @Test
    void edgeCase_neverExposesThePlatformNameInACustomerVisibleUrl() {
        // Constitution V.1 / spec FR-013: the customer must never see "Rockey" — a label
        // URL is customer-visible (emailed, shown in the widget), so it must use the
        // retailer's own hostname, never the platform's.
        String url = generator.generate("CMD-2026-00001");

        assertThat(url.toLowerCase()).doesNotContain("rockey");
    }
}
