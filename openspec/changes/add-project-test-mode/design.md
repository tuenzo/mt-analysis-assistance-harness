## Design

Test mode is controlled by `APP_TEST_MODE`. The setting defaults to `false`.

When test mode is active, newly created projects are marked with `is_test = true`. Normal project loading paths exclude test projects unless test mode is active. This keeps test fixtures available for automated test runs while preventing them from appearing in the everyday workspace.

For the MVP SQLite database, startup performs a small additive compatibility check that adds `projects.is_test` when an existing local database predates the column. This avoids requiring developers to delete their database just to pick up the metadata field.
