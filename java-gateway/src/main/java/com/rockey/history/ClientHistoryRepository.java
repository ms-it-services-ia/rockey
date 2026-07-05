package com.rockey.history;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ClientHistoryRepository extends JpaRepository<ClientHistory, UUID> {

    Optional<ClientHistory> findByTenantIdAndClientEmail(String tenantId, String clientEmail);
}
