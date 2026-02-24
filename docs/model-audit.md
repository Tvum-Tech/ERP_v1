# Model Audit: Project, Product, Driver, Accessory

This audit reviews the current Django models for BOQ-oriented ERP usage:

- `apps/projects/models.py`
- `apps/masters/models/product.py`
- `apps/masters/models/driver.py`
- `apps/masters/models/accessory.py`

## Overall verdict

The structure is close to your target workflow (`Project > Area > SubArea > Configuration > BOQ`), but there are several correctness and maintainability issues that should be fixed before production use.

## Critical correctness issues

1. **`Project.project_code` is required but generated after initial save**
   - The field is currently declared as required (`unique=True` with no `blank=True` / `null=True`).
   - The `save()` method tries to generate it only *after* the first `super().save()`, so object creation can fail unless caller provides `project_code` manually.

2. **`Project.refered_by` is invalid Django field declaration**
   - It is declared as `models.CharField(blank=True, null=True)` without a required `max_length`.
   - This should raise model import/runtime errors.

3. **`base_price` defaults are effectively static random values**
   - In Product/Driver/Accessory models, `default=random.randint(1,99)` is executed at import time.
   - Every new row in the process gets the same default until restart. Use a callable instead.

## Data quality / modeling concerns

1. **Choice value with spaces (`TRACK MOUNTED`)**
   - Used in Product and Accessory compatibility lists.
   - Safer pattern is stable machine values (e.g., `TRACK_MOUNTED`) and human labels separately.

2. **Mixed naming / typos reduce API clarity**
   - `segement_choice`, `refered_by`, `expecetd_mhr`, `lumen_efficency`, `cri_cci`.
   - Consider consistent snake_case with corrected spellings.

3. **Project financial fields are strict**
   - `fee` is mandatory. If inquiries can be created before commercial estimate, make it nullable or defaulted.

4. **Validation gaps**
   - Several numeric fields (IP class, wattage, voltage/current ranges) have no min/max validators.
   - Add validators to prevent impossible values.

## Workflow fit vs BOQ goal

Good fit:
- `Project -> Area -> SubArea` hierarchy is present and consistent.
- Unique constraints for area/subarea names within parent are good.

Missing for robust BOQ generation:
- No explicit `Configuration` model linking product + driver + accessory sets per area/subarea.
- No versioned BOQ snapshot model in this audit scope.
- Compatibility constraints (product electrical type vs driver constant type, mounting style compatibility) are not enforced at model level.

## Recommended fixes (priority order)

1. Fix Project model correctness:
   - Make `project_code` nullable/blank during first save or generate before save.
   - Add `max_length` to `refered_by`.

2. Replace random defaults with callable defaults:
   - e.g., `default=get_default_price` where function returns deterministic Decimal.

3. Introduce configuration entities:
   - `ConfigurationTemplate`, `SubAreaConfiguration`, `BOQRevision`, `BOQLine`.

4. Add validators + naming cleanup in a backward-compatible migration plan.

## Suggested next implementation step

Implement a `Configuration` app that stores each selected `Product + Driver + Accessories` combination per `SubArea`, then a BOQ service that expands and aggregates quantities by revision.
