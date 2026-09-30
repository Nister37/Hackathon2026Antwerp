package be.kdg.hackathon2026antwerp.dto;

import java.math.BigDecimal;
import java.time.LocalDate;

public record TransactionDto(
        LocalDate date,
        BigDecimal amount,
        String merchant,
        String category,
        String city
) {
}
