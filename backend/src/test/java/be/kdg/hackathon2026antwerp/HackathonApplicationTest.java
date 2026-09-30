package be.kdg.hackathon2026antwerp;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class HackathonApplicationTest {
    @Autowired
    private MockMvc mockMvc;

    @Test
    void contextLoads() {
    }

    @Test
    void healthEndpointIsPublic() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void exposesOnlyTheTwoConfiguredUsers() throws Exception {
        mockMvc.perform(get("/api/users"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value("1"))
                .andExpect(jsonPath("$[0].displayName").value("Tom"))
                .andExpect(jsonPath("$[1].id").value("2"))
                .andExpect(jsonPath("$[1].displayName").value("Maria"))
                .andExpect(jsonPath("$[2]").doesNotExist());
    }

    @Test
    void readsRecentTransactionsFromCsvWithoutExposingIdentifiers() throws Exception {
        mockMvc.perform(get("/api/users/1/transactions?limit=3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].merchant").value("Colruyt"))
                .andExpect(jsonPath("$[0].date").value("2026-08-31"))
                .andExpect(jsonPath("$[2]").exists())
                .andExpect(jsonPath("$[3]").doesNotExist())
                .andExpect(jsonPath("$[0].transactionId").doesNotExist())
                .andExpect(jsonPath("$[0].customerId").doesNotExist());
    }

    @Test
    void rejectsUnknownUsersAndInvalidLimits() throws Exception {
        mockMvc.perform(get("/api/users/3/transactions"))
                .andExpect(status().isNotFound());
        mockMvc.perform(get("/api/users/1/transactions?limit=9"))
                .andExpect(status().isBadRequest());
        mockMvc.perform(get("/api/users/3/insight"))
                .andExpect(status().isNotFound());
    }

    @Test
    void exposesOnlyExplanationFieldsFromMatchingMlArtifact() throws Exception {
        mockMvc.perform(get("/api/users/1/insight"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Possible travel pattern"))
                .andExpect(jsonPath("$.evidence[0]").value("Travel spend is EUR 1,869.50"))
                .andExpect(jsonPath("$.confidence_percent").doesNotExist())
                .andExpect(jsonPath("$.customer_id").doesNotExist());
        mockMvc.perform(get("/api/users/2/insight"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Possible home pattern"));
    }

    @Test
    void scopesCorsToTheConfiguredFrontendOrigin() throws Exception {
        mockMvc.perform(options("/api/users")
                        .header("Origin", "http://localhost:4200")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:4200"));
        mockMvc.perform(get("/api/users").header("Origin", "https://untrusted.example"))
                .andExpect(status().isForbidden());
    }

    @Test
    void keepsCsrfProtectionAndSecurityHeaders() throws Exception {
        mockMvc.perform(post("/api/users/1/transactions"))
                .andExpect(status().isForbidden());
        mockMvc.perform(get("/api/users"))
                .andExpect(header().string("X-Content-Type-Options", "nosniff"))
                .andExpect(header().string("X-Frame-Options", "DENY"))
                .andExpect(header().string("Referrer-Policy", "no-referrer"))
                .andExpect(header().string("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"))
                .andExpect(header().string("Permissions-Policy", "camera=(), microphone=(), geolocation=()"));
    }
}
