package example.fixture;

import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/profile")
public class ProfileController {
    private final RiskProfileService service;

    public ProfileController(RiskProfileService service) {
        this.service = service;
    }

    @PostMapping("/drafts")
    public ProfileDtos.Draft start(@Valid @RequestBody ProfileDtos.StartDraft request) {
        return service.start(request.investorRef());
    }

    @PatchMapping("/drafts/{draftId}")
    public ProfileDtos.Draft save(@PathVariable String draftId, @Valid @RequestBody ProfileDtos.Answers answers) {
        return service.save(draftId, answers);
    }

    @PostMapping("/drafts/{draftId}/submit")
    public ProfileDtos.Assessment submit(@PathVariable String draftId, @Valid @RequestBody ProfileDtos.Submit request) {
        return service.submit(draftId, request.idempotencyKey());
    }

    @GetMapping("/investors/{investorRef}/history")
    public List<ProfileDtos.Assessment> history(@PathVariable String investorRef) {
        return service.history(investorRef);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public String invalid(IllegalArgumentException error) {
        return error.getMessage();
    }

    @ExceptionHandler(IllegalStateException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    public String conflict(IllegalStateException error) {
        return error.getMessage();
    }
}
