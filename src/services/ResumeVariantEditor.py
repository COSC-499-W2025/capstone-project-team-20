from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, List


class ResumeVariantEditor:
    """
    Interactive CLI editor for a resume "context" dictionary used by ReportExporter.

    Edits the in-memory context (via deepcopy) and returns a new context:
      - Header fields (name/email/phone/links)
      - Project info (name/stack/dates)
      - Project bullets (add/edit/delete/reorder)
    """

    def edit_variant_cli(self, base_context: Dict[str, Any]) -> Dict[str, Any]:
        ctx = deepcopy(base_context)
        projects: List[Dict[str, Any]] = ctx.get("projects", []) or []
        if not projects:
            print("No projects found to edit.")
            return ctx

        while True:
            print("\n==============================")
            print(" Resume Variant Editor")
            print("==============================")
            print("1) Edit header (name/email/phone/links)")
            print("2) Edit project bullets")
            print("3) Edit project info (name/stack/dates)")
            print("q) Done")
            top = input("> ").strip().lower()

            if top == "q":
                return ctx

            if top == "1":
                self._edit_resume_header_cli(ctx)
                continue

            if top == "3":
                self._pick_project_and_edit_info(projects)
                ctx["projects"] = projects
                continue

            if top == "2":
                self._pick_project_and_edit_bullets(projects)
                ctx["projects"] = projects
                continue

            print("Invalid selection.")

    # -------------------------
    # Header / Project Info
    # -------------------------

    def _edit_resume_header_cli(self, ctx: Dict[str, Any]) -> None:
        print("\n--- Edit Header ---")
        for key in ["name", "email", "phone", "github_display", "linkedin_display"]:
            cur = ctx.get(key, "")
            new_val = input(f"{key} [{cur}]: ").strip()
            if new_val:
                ctx[key] = new_val

    def _edit_project_info_cli(self, proj: Dict[str, Any]) -> None:
        print(f"\n--- Edit Project Info: {proj.get('name','Project')} ---")
        for key in ["name", "stack", "dates"]:
            cur = proj.get(key, "")
            new_val = input(f"{key} [{cur}]: ").strip()
            if new_val:
                proj[key] = new_val

    def _pick_project_and_edit_info(self, projects: List[Dict[str, Any]]) -> None:
        print("\nSelect a project to edit info:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}) {p.get('name','Project')}")
        print("  q) Back")

        pick = input("> ").strip().lower()
        if pick == "q":
            return
        if not pick.isdigit():
            print("Please enter a number or q.")
            return

        idx = int(pick) - 1
        if not (0 <= idx < len(projects)):
            print("Invalid project number.")
            return

        self._edit_project_info_cli(projects[idx])

    # -------------------------
    # Bullets
    # -------------------------

    def _pick_project_and_edit_bullets(self, projects: List[Dict[str, Any]]) -> None:
        print("\nSelect a project to edit bullets:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}) {p.get('name','Project')}")
        print("  q) Back")

        choice = input("> ").strip().lower()
        if choice == "q":
            return
        if not choice.isdigit():
            print("Please enter a number or q.")
            return

        idx = int(choice) - 1
        if not (0 <= idx < len(projects)):
            print("Invalid project number.")
            return

        proj = projects[idx]
        bullets = proj.get("bullets", []) or []
        self._edit_bullets_cli(proj.get("name", "Project"), bullets)
        proj["bullets"] = bullets
        projects[idx] = proj

    def _edit_bullets_cli(self, project_name: str, bullets: List[str]) -> None:
        while True:
            print(f"\n--- Bullets for {project_name} ---")
            if not bullets:
                print("(none)")
            for j, b in enumerate(bullets, 1):
                print(f"  {j}) {b}")

            print("\nOptions:")
            print("  1) Edit bullet")
            print("  2) Add bullet")
            print("  3) Delete bullet")
            print("  4) Move bullet up/down")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                n = input("Bullet # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(bullets):
                    new_txt = input("New text: ").strip()
                    if new_txt:
                        bullets[int(n) - 1] = new_txt
                else:
                    print("Invalid bullet number.")

            elif sub == "2":
                new_txt = input("New bullet: ").strip()
                if new_txt:
                    bullets.append(new_txt)

            elif sub == "3":
                n = input("Bullet # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(bullets):
                    bullets.pop(int(n) - 1)
                else:
                    print("Invalid bullet number.")

            elif sub == "4":
                n = input("Bullet # to move: ").strip()
                if not (n.isdigit() and 1 <= int(n) <= len(bullets)):
                    print("Invalid bullet number.")
                    continue
                direction = input("u=up, d=down: ").strip().lower()
                i = int(n) - 1
                if direction == "u" and i > 0:
                    bullets[i - 1], bullets[i] = bullets[i], bullets[i - 1]
                elif direction == "d" and i < len(bullets) - 1:
                    bullets[i + 1], bullets[i] = bullets[i], bullets[i + 1]
                else:
                    print("Can't move that way.")

            elif sub == "5":
                return

            else:
                print("Invalid selection.")
