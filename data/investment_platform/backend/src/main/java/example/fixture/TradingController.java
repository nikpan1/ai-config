package example.fixture;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.HttpServerErrorException;

@RestController
@RequestMapping("/api/trading")
public class TradingController {
    private final RestClient market;
    private final RestClient custody;
    private final OrderRepository orders;

    public TradingController(@Value("${fixture.market-pulse-url}") String marketUrl, @Value("${fixture.custody-bridge-url}") String custodyUrl, OrderRepository orders) {
        market = client(marketUrl, Duration.ofMillis(800));
        custody = client(custodyUrl, Duration.ofSeconds(3));
        this.orders = orders;
    }

    @GetMapping("/quotes/{instrumentId}")
    public Map quote(@PathVariable String instrumentId) {
        try {
            return market.get().uri("/quotes/{instrumentId}", instrumentId).retrieve().body(Map.class);
        } catch (HttpServerErrorException.ServiceUnavailable retryable) {
            return market.get().uri("/quotes/{instrumentId}", instrumentId).retrieve().body(Map.class);
        }
    }

    @PostMapping("/orders/{orderRef}/reserve")
    public Map reserve(@PathVariable String orderRef) {
        Map<String, Object> order = orders.order(orderRef);
        Map<String, Object> request = Map.of("accountRef", order.get("account_ref"), "orderRef", orderRef, "amount", order.get("amount"), "currency", order.get("currency"), "reservationKey", order.get("reservation_key"), "correlationId", "order-" + orderRef);
        Map response = custody.post().uri("/reservations").body(request).retrieve().body(Map.class);
        if (response == null || !"RESERVED".equals(response.get("reservationStatus")) || response.get("reservationId") == null) throw new IllegalStateException("Reservation not accepted");
        orders.reserved(orderRef, response.get("reservationId").toString());
        return response;
    }

    private RestClient client(String baseUrl, Duration timeout) {
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(timeout).build());
        factory.setReadTimeout(timeout);
        return RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
    }
}
