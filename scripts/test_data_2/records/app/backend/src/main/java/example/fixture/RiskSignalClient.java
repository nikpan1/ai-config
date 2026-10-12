package example.fixture;

import java.time.Duration;
import java.net.http.HttpClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class RiskSignalClient {
    private final RestClient http;

    public RiskSignalClient(@Value("${fixture.risk-signal-url}") String baseUrl) {
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build());
        factory.setReadTimeout(Duration.ofSeconds(2));
        http = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
    }

    public ProfileDtos.ProviderResponse assess(ProfileDtos.ProviderRequest request) {
        return http.post().uri("/assessments").body(request).retrieve().body(ProfileDtos.ProviderResponse.class);
    }
}
