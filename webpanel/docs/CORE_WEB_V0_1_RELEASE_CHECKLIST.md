# Core + Web v0.1 Release Checklist

Date: 2026-06-16

Scope: Core + Web only. This checklist intentionally excludes Docker, KVM, Remote Access, Cloudflare/DNS, SSL automation, PHP-FPM management, file upload/edit/delete/download, and production installer hardening.

## Result

Overall result: **Pass for controlled v0.1 lab/admin release, with Ubuntu lab rerun blocked by reachability.**

## Local Validation

| Check | Result | Evidence |
| --- | --- | --- |
| Correct workspace used | Pass | `C:\Users\Admin\OneDrive\Documentos\HostPilot_RECOVERY_CLEAN\webpanel` |
| Backend service running | Pass | `http://127.0.0.1:8000/health` returned HTTP `200` |
| Frontend service running | Pass | `http://127.0.0.1:5173/` returned HTTP `200` |
| Backend pytest | Pass | `108 passed` |
| Agent pytest | Pass | `27 passed` |
| Frontend build | Pass | `npm run build` completed successfully |
| Browser smoke check | Pass | Login form worked with temporary validation user; Web page rendered without console errors |
| Temporary validation user cleanup | Pass | Temporary browser validation account was deactivated after the check |

## Core Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Login | Pass | JWT login works through API and browser flow. |
| Logout | Pass | Frontend clears token/user state and backend logout endpoint records audit when reachable. |
| Token expiry handling | Pass | Authenticated 401 responses dispatch `hostpilot:auth-expired` and clear session state. |
| Admin bootstrap safety | Pass | Existing admin passwords are not reset unless `--reset-password` is provided. |
| RBAC enforcement | Pass | Core/Web APIs use permission dependencies; current local admin has Web permissions. |
| Users UI/API | Pass | User create/update/reset endpoints are tested; UI surfaces API errors. |
| Roles visibility | Pass | Roles/permissions are inspectable. |
| Admin lockout guards | Pass | Backend blocks self-deactivation, last admin deactivation, and admin-access removal lockouts. |
| Audit log | Pass | Implemented Core/Web mutations record audit events. |
| Jobs | Pass | Jobs list is visible; dev-only mock job creation is hidden unless dev mode is enabled. |
| Notifications | Pass | List/read/read-all flows exist. |
| Core backups | Limited | Basic archive creation exists; restore/scheduling/remote storage are later work. |
| Agent status | Pass | UI/backend distinguish `connected`, `fallback`, and `unavailable`. |
| Dev/mock actions | Pass | Hidden by default and labeled development-only when enabled. |

## Web Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Web module visibility | Pass | Route/sidebar entry works under RBAC/module visibility. |
| Site create on Windows | Pass | Created `v01-local-20260616153459.local` without Agent/Nginx. |
| Root path derivation | Pass | Root path derived as `/var/www/hostpilot-sites/v01-local-20260616153459.local`. |
| Client root path override blocked | Pass | Create API ignores client root-path input and derives server-side. |
| Site list | Pass | Created site appears in the local Web site list. |
| Row actions | Pass | Row Actions menu contains Files, Logs, Preview, Mark Ready, Plan / Dry-run / Apply, Disable record, Disable site, and Re-Apply. |
| Files read-only viewer | Pass | Endpoint/UI are wired; metadata-only and path constrained. |
| Logs read-only viewer | Pass | Endpoint/UI are wired; read-only and max-line constrained. |
| Nginx preview | Pass | Preview generated text only, no file writes. |
| Readiness | Pass | Site marked `ready_to_apply` after validation/preview. |
| Apply plan | Pass | Plan generated for ready site. |
| Dry-run | Pass | Dry-run completed with `executed: false`, no writes or commands. |
| Preflight | Pass | Local Windows state reported `fallback` and `ready: false`. |
| Controlled apply local gate | Pass | Apply attempt was blocked with HTTP `409` while Agent was fallback. |
| Controlled disable/reapply local gate | Pass | UI disables Agent-backed lifecycle actions without real Agent. |

## Ubuntu Lab Checklist

| Check | Result | Notes |
| --- | --- | --- |
| SSH port reachability | Pass | `192.168.0.64:22` is reachable. |
| SSH password authentication | Blocked | Supplied password was rejected for both `rattes` and `root`. |
| SSH key installation | Blocked | Requires successful password login first. |
| SSH alias validation | Blocked | `hostpilot-lab` points to `rattes@192.168.0.64` with `~/.ssh/hostpilot_lab`, but passwordless login cannot pass until the public key is installed. |
| OS/version | Not run | Blocked by SSH authentication. |
| Sudo/root access | Not run | Blocked by SSH authentication. |
| Deploy latest main | Not run | Blocked by SSH authentication. |
| Run migrations | Not run | Blocked by SSH authentication. |
| Restart Core/Agent/Nginx | Not run | Blocked by SSH authentication. |
| Core health on lab | Not run | Blocked by SSH authentication. |
| Agent health on lab | Not run | Blocked by SSH authentication. |
| UI HTTP 200 on lab | Not run | Blocked by SSH authentication. |
| Login on lab | Not run | Blocked by SSH authentication. |
| Web create/list on lab | Not run | Blocked by SSH authentication. |
| Files/Logs on lab | Not run | Blocked by SSH authentication. |
| Preview/plan/dry-run/preflight on lab | Not run | Blocked by SSH authentication. |
| Controlled apply/disable/reapply on lab | Not run | Blocked by SSH authentication. |
| Audit/job records on lab | Not run | Blocked by SSH authentication. |

Previous controlled Nginx apply validation on the Ubuntu lab is documented in `docs/deploy/ubuntu-lab-deploy.md`.

## Release Decision

Proceed with Core + Web v0.1 as a controlled lab/admin release after acknowledging the following conditions:

- controlled Nginx actions must only be used when Web preflight passes with Agent state `connected`;
- Windows development is valid for records, preview, readiness, plan, and dry-run, but not real Nginx apply;
- the latest Ubuntu lab validation must be rerun before claiming current-lab validation for this exact commit;
- documented limitations remain out of scope for v0.1.
