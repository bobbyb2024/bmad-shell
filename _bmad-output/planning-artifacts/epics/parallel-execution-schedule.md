# Parallel Execution Schedule

```
Phase 1:  Epic 1 (Foundation & Config)
Phase 2:  Epic 2 (Providers)
Phase 3:  Epic 3 (Engine)          ║  Epic 6 (Init Wizard)
Phase 4:  Epic 4 (Unattended)      ║  Epic 6 (cont. if needed)
Phase 5:  Epic 5 (TUI)  ║  Epic 7 (Lite Mode)  ║  Epic 6 (cont. if needed)
```

**Dependency Rules:**
- Epics 1 → 2 → 3 → 4: strictly sequential (each builds on the previous)
- Epic 6 starts after Epic 2 (needs config schema + provider detection); independent of Epics 3-5 and 7
- Epics 5 and 7 start after Epic 4 (need the complete engine to render); independent of each other and Epic 6
- All three presentation epics (5, 6, 7) touch separate code modules and can build simultaneously without interference
