# Contributing Guidelines

Thank you for contributing to **SIH-26074-AgroWeather-Downscaling**!

This project is prepared for the **Smart India Hackathon (Problem Statement 26074)** evaluation. To maintain stability, code quality, and scientific integrity, all team members and contributors are requested to adhere to the following workflow and guidelines.

---

## 🌿 Git Branching Strategy

The default branch is `main`. All active development should take place on short-lived feature or bugfix branches:

```
main  ──────────────────────────────────────────► (Stable SIH Evaluation Baseline)
        \                                    /
         └── feature/<short-description> ───┘ (Pull Request + Review)
```

### Branch Naming Conventions:
* `feature/<feature-name>` — For new capabilities, scripts, or components
* `fix/<bug-description>` — For bug fixes or corrections
* `docs/<topic>` — For documentation improvements or presentation updates
* `test/<component>` — For new unit, integration, or regression tests
* `refactor/<module>` — For code cleanup without functional changes

---

## 🔄 Development Workflow

1. **Synchronize with Main**:
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Focused Changes**:
   - Write clean, well-documented code.
   - Keep pull requests scoped to a single logical change.

4. **Verify Locally**:
   - Run backend tests:
     ```bash
     cd backend
     pytest -v
     ```
   - Run frontend build:
     ```bash
     cd frontend
     npm run build
     ```
   - Validate canonical demo pipeline:
     ```bash
     python backend/scripts/validate_demo_scenario.py --date 2026-07-15
     ```

5. **Commit with Conventional Commit Messages**:
   Follow standard commit prefix conventions:
   - `feat:` — A new feature
   - `fix:` — A bug fix
   - `docs:` — Documentation only changes
   - `test:` — Adding or modifying tests
   - `refactor:` — Code change that neither fixes a bug nor adds a feature
   - `chore:` — Maintenance tasks, configuration, or dependency updates

   *Example:*
   ```bash
   git commit -m "feat: add soil moisture saturation index to agricultural context"
   ```

6. **Push and Open Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Open a Pull Request targeting `main` on GitHub. Ensure PR description details what was changed and how it was tested.

---

## 🛡️ Critical Evaluation Safeguards

> [!IMPORTANT]
> The current system is **SIH Evaluation Ready**. Do NOT casually modify or delete core evaluation-critical components:
> - Canonical demonstration scripts (`backend/scripts/seed_demo_scenario.py`, `validate_demo_scenario.py`, `reset_demo_scenario.py`)
> - SIH Judge Mode (`frontend/src/pages/JudgeMode.tsx`)
> - Scientific safety guardrails (No disease diagnosis, no chemical pesticide dosages, coarse rainfall preservation)
> - Machine learning residual formulation ($\hat{R}(x,y) = T_{\text{downscaled}} - T_{\text{coarse}}$)

---

## 🔒 Security Best Practices

- **NEVER** commit `.env` files, API keys, database passwords, or private tokens.
- Always use environment variables loaded through `backend/app/core/config.py` or `frontend/.env`.
- Update `.env.example` if new environment variables are introduced.
