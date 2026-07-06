package com.rockey.history;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ClientHistoryServiceTest {

    @Mock private ClientHistoryRepository repository;

    private ClientHistoryService clientHistoryService;

    @BeforeEach
    void setUp() {
        clientHistoryService = new ClientHistoryService(repository);
        when(repository.save(org.mockito.ArgumentMatchers.any(ClientHistory.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    void happyPath_firstComplaintFromANewCustomerIsNotARepeat() {
        when(repository.findByTenantIdAndClientEmail("vinted", "sophie.bernard@email.com")).thenReturn(Optional.empty());

        var result = clientHistoryService.recordComplaint("vinted", "sophie.bernard@email.com");

        assertThat(result.priorComplaintCount()).isEqualTo(0);
        assertThat(result.isRepeat()).isFalse();

        ArgumentCaptor<ClientHistory> captor = ArgumentCaptor.forClass(ClientHistory.class);
        verify(repository).save(captor.capture());
        assertThat(captor.getValue().getComplaintCount()).isEqualTo(1);
        assertThat(captor.getValue().getLastContact()).isNotNull();
    }

    @Test
    void edgeCase_secondComplaintFromTheSameCustomerIsFlaggedAsRepeat() {
        ClientHistory existing = new ClientHistory("vinted", "sophie.bernard@email.com");
        existing.setComplaintCount(1);
        when(repository.findByTenantIdAndClientEmail("vinted", "sophie.bernard@email.com")).thenReturn(Optional.of(existing));

        var result = clientHistoryService.recordComplaint("vinted", "sophie.bernard@email.com");

        assertThat(result.priorComplaintCount()).isEqualTo(1);
        assertThat(result.isRepeat()).isTrue();

        ArgumentCaptor<ClientHistory> captor = ArgumentCaptor.forClass(ClientHistory.class);
        verify(repository).save(captor.capture());
        assertThat(captor.getValue().getComplaintCount()).isEqualTo(2);
    }
}
