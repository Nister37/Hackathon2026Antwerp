package be.kdg.hackathon2026antwerp.dto;

import java.util.List;

public record InsightDto(String title, String summary, List<String> evidence) {
}
