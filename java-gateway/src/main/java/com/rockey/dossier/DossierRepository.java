package com.rockey.dossier;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DossierRepository extends JpaRepository<Dossier, UUID> {}
