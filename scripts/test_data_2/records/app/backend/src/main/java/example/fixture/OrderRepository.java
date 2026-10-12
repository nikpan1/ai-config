package example.fixture;

import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class OrderRepository {
    private final JdbcTemplate db;

    public OrderRepository(JdbcTemplate db) {
        this.db = db;
    }

    public Map<String, Object> order(String orderRef) {
        return db.queryForMap("select order_ref, account_ref, instrument_id, amount, currency, state, reservation_key from order_record where order_ref = ?", orderRef);
    }

    public void reserved(String orderRef, String reservationId) {
        int changed = db.update("update order_record set state = 'RESERVED', reservation_id = ? where order_ref = ? and state = 'NEW'", reservationId, orderRef);
        if (changed != 1) throw new IllegalStateException("Order is not NEW");
    }
}
