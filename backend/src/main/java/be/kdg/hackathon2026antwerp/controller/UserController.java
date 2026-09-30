package be.kdg.hackathon2026antwerp.controller;

import be.kdg.hackathon2026antwerp.dto.TransactionDto;
import be.kdg.hackathon2026antwerp.dto.InsightDto;
import be.kdg.hackathon2026antwerp.dto.UserSummaryDto;
import be.kdg.hackathon2026antwerp.service.TransactionCsvService;
import be.kdg.hackathon2026antwerp.service.ProfileInsightService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final TransactionCsvService transactions;
    private final ProfileInsightService insights;

    public UserController(TransactionCsvService transactions, ProfileInsightService insights) {
        this.transactions = transactions;
        this.insights = insights;
    }

    @GetMapping
    public List<UserSummaryDto> users() {
        return transactions.users();
    }

    @GetMapping("/{userId}/transactions")
    public List<TransactionDto> recentTransactions(
            @PathVariable String userId,
            @RequestParam(defaultValue = "8") int limit
    ) {
        if (limit < 1 || limit > 8) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Limit must be between 1 and 8");
        }
        return transactions.recentTransactions(userId, limit);
    }

    @GetMapping("/{userId}/insight")
    public InsightDto insight(@PathVariable String userId) {
        return insights.forUser(userId);
    }
}
