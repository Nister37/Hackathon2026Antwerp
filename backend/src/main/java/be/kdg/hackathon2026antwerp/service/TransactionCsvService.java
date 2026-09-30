package be.kdg.hackathon2026antwerp.service;

import be.kdg.hackathon2026antwerp.dto.TransactionDto;
import be.kdg.hackathon2026antwerp.dto.UserSummaryDto;
import jakarta.annotation.PostConstruct;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.io.Reader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

@Service
public class TransactionCsvService {
    private static final Map<String, String> FILES = Map.of(
            "1", "tom_transactions.csv",
            "2", "maria_transactions.csv"
    );
    private static final List<UserSummaryDto> USERS = List.of(
            new UserSummaryDto("1", "Tom"),
            new UserSummaryDto("2", "Maria")
    );

    private final Path directory;
    private Map<String, List<TransactionDto>> transactions;

    public TransactionCsvService(@Value("${app.transactions.directory}") String directory) {
        this.directory = Path.of(directory).toAbsolutePath().normalize();
    }

    @PostConstruct
    void load() {
        try {
            transactions = Map.of(
                    "1", read(FILES.get("1")),
                    "2", read(FILES.get("2"))
            );
        } catch (IOException | IllegalArgumentException exception) {
            throw new IllegalStateException("Could not load the configured transaction CSV files", exception);
        }
    }

    public List<UserSummaryDto> users() {
        return USERS;
    }

    public List<TransactionDto> recentTransactions(String userId, int limit) {
        List<TransactionDto> records = transactions.get(userId);
        if (records == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found");
        }
        return records.stream().limit(limit).toList();
    }

    private List<TransactionDto> read(String fileName) throws IOException {
        Path file = directory.resolve(fileName);
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).get().parse(reader)) {
            List<TransactionDto> records = parser.stream().map(this::toDto)
                    .sorted(Comparator.comparing(TransactionDto::date).reversed()).toList();
            if (records.isEmpty()) {
                throw new IllegalArgumentException("Transaction CSV is empty: " + fileName);
            }
            return records;
        }
    }

    private TransactionDto toDto(CSVRecord record) {
        return new TransactionDto(
                LocalDate.parse(record.get("date")),
                new BigDecimal(record.get("amount")),
                record.get("merchant"),
                record.get("category"),
                record.get("city")
        );
    }
}
