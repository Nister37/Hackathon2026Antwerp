package be.kdg.hackathon2026antwerp.service;

import be.kdg.hackathon2026antwerp.dto.InsightDto;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.stream.StreamSupport;

@Service
public class ProfileInsightService {
    private static final Map<String, String> CUSTOMERS = Map.of("1", "TOM", "2", "MARIA");
    private static final Map<String, String> SOURCES = Map.of(
            "TOM", "tom_transactions.csv", "MARIA", "maria_transactions.csv"
    );

    private final Path profileFile;
    private final Path transactionDirectory;
    private final ObjectMapper mapper;
    private Map<String, InsightDto> insights;

    public ProfileInsightService(
            @Value("${app.insights.file}") String profileFile,
            @Value("${app.transactions.directory}") String transactionDirectory,
            ObjectMapper mapper
    ) {
        this.profileFile = Path.of(profileFile).toAbsolutePath().normalize();
        this.transactionDirectory = Path.of(transactionDirectory).toAbsolutePath().normalize();
        this.mapper = mapper;
    }

    @PostConstruct
    void load() {
        try {
            JsonNode artifact = mapper.readTree(Files.readAllBytes(profileFile));
            if (artifact.path("schema_version").asInt() != 1) {
                throw new IllegalArgumentException("Unsupported profile artifact schema");
            }
            for (String fileName : SOURCES.values()) {
                String expected = artifact.path("source_sha256").path(fileName).asText();
                String actual = HexFormat.of().formatHex(
                        MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(transactionDirectory.resolve(fileName)))
                );
                if (!actual.equals(expected)) {
                    throw new IllegalArgumentException("Profile artifact does not match transaction CSV: " + fileName);
                }
            }
            JsonNode cards = artifact.path("suggestions");
            if (!cards.isArray() || cards.size() != 2) {
                throw new IllegalArgumentException("Expected exactly two demo profile cards");
            }
            Map<String, InsightDto> loaded = new java.util.HashMap<>();
            for (JsonNode card : cards) {
                String customer = card.path("customer_id").asText();
                JsonNode evidence = card.path("evidence");
                if (!SOURCES.containsKey(customer) || loaded.containsKey(customer) || !evidence.isArray() || evidence.size() < 2) {
                    throw new IllegalArgumentException("Invalid demo profile card");
                }
                List<String> details = StreamSupport.stream(evidence.spliterator(), false)
                        .limit(2)
                        .map(item -> item.path("display").asText())
                        .toList();
                String title = card.path("title").asText();
                String summary = card.path("summary").asText();
                if (title.isBlank() || summary.isBlank() || details.stream().anyMatch(String::isBlank)) {
                    throw new IllegalArgumentException("Incomplete demo profile card");
                }
                loaded.put(customer, new InsightDto(title, summary, details));
            }
            if (!loaded.keySet().equals(SOURCES.keySet())) {
                throw new IllegalArgumentException("Missing demo profile card");
            }
            insights = Map.copyOf(loaded);
        } catch (IOException | NoSuchAlgorithmException | IllegalArgumentException exception) {
            throw new IllegalStateException("Could not load matching ML profile artifact", exception);
        }
    }

    public InsightDto forUser(String userId) {
        String customer = CUSTOMERS.get(userId);
        if (customer == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found");
        }
        return insights.get(customer);
    }
}
