from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


class ResumeVariantEditor:
    """
    Interactive CLI editor for a resume "context" dictionary used by ReportExporter.

    Edits the in-memory context (via deepcopy) and returns a new context:
      - Header fields (name/email/phone/github/linkedin)
      - Education entries
      - Experience entries
      - Projects (name/stack/dates + bullets)
      - Technical skills (categories + items)
    """

    # -------------------------
    # Public entry
    # -------------------------

    def edit_variant_cli(self, base_context: Dict[str, Any]) -> Dict[str, Any]:
        ctx = deepcopy(base_context)

        # Ensure common keys exist so menus don’t crash
        ctx.setdefault("education", ctx.get("education") or [])
        ctx.setdefault("experience", ctx.get("experience") or [])
        ctx.setdefault("skills", ctx.get("skills") or {})
        ctx.setdefault("projects", ctx.get("projects") or [])

        while True:
            print("\n==============================")
            print(" Resume Variant Editor")
            print("==============================")
            print("1) Edit header (name/email/phone/links)")
            print("2) Edit projects (info + bullets)")
            print("3) Edit education")
            print("4) Edit experience")
            print("5) Edit technical skills")
            print("q) Done")
            top = input("> ").strip().lower()

            if top == "q":
                return ctx

            if top == "1":
                self._edit_resume_header_cli(ctx)
                continue

            if top == "2":
                self._edit_projects_menu(ctx)
                continue

            if top == "3":
                self._edit_education_menu(ctx)
                continue

            if top == "4":
                self._edit_experience_menu(ctx)
                continue

            if top == "5":
                self._edit_skills_menu(ctx)
                continue

            print("Invalid selection.")

    # -------------------------
    # Header
    # -------------------------

    def _edit_resume_header_cli(self, ctx: Dict[str, Any]) -> None:
        """
        Your LaTeX header uses:
          - name, phone, email
          - github_url, github_display
          - linkedin_url, linkedin_display

        So we edit those *exact* keys, and we also accept a handle for GH/LI and build url+display.
        """
        print("\n--- Edit Header ---")

        # Basic fields
        for key in ["name", "email", "phone"]:
            cur = (ctx.get(key) or "").strip()
            new_val = input(f"{key} [{cur}]: ").strip()
            if new_val:
                ctx[key] = new_val

        # GitHub
        gh_display = (ctx.get("github_display") or "").strip()
        gh_url = (ctx.get("github_url") or "").strip()
        gh_cur = gh_display or gh_url
        gh_in = input(f"github (handle or url) [{gh_cur}]: ").strip()
        if gh_in:
            g_url, g_disp = self._normalize_github(gh_in)
            ctx["github_url"] = g_url
            ctx["github_display"] = g_disp

        # LinkedIn
        li_display = (ctx.get("linkedin_display") or "").strip()
        li_url = (ctx.get("linkedin_url") or "").strip()
        li_cur = li_display or li_url
        li_in = input(f"linkedin (handle or url) [{li_cur}]: ").strip()
        if li_in:
            l_url, l_disp = self._normalize_linkedin(li_in)
            ctx["linkedin_url"] = l_url
            ctx["linkedin_display"] = l_disp

    def _normalize_github(self, raw: str) -> Tuple[str, str]:
        raw = raw.strip()

        # Full URL
        if raw.startswith("http://") or raw.startswith("https://"):
            url = raw
            disp = raw.replace("https://", "").replace("http://", "").rstrip("/")
            return url.rstrip("/"), disp

        # Possibly "github.com/user"
        raw = raw.replace("github.com/", "").strip().strip("/")
        handle = raw
        url = f"https://github.com/{handle}"
        disp = f"github.com/{handle}"
        return url, disp

    def _normalize_linkedin(self, raw: str) -> Tuple[str, str]:
        raw = raw.strip()

        # Full URL
        if raw.startswith("http://") or raw.startswith("https://"):
            url = raw.rstrip("/")
            disp = raw.replace("https://", "").replace("http://", "").rstrip("/")
            return url, disp

        # Possibly "linkedin.com/in/handle"
        raw = raw.replace("linkedin.com/in/", "").strip().strip("/")
        handle = raw
        url = f"https://linkedin.com/in/{handle}"
        disp = f"linkedin.com/in/{handle}"
        return url, disp

    # -------------------------
    # Projects
    # -------------------------

    def _edit_projects_menu(self, ctx: Dict[str, Any]) -> None:
        projects: List[Dict[str, Any]] = ctx.get("projects", []) or []
        if not projects:
            print("No projects found to edit.")
            return

        while True:
            print("\n--- Projects ---")
            print("1) Edit project info (name/stack/dates)")
            print("2) Edit project bullets")
            print("3) Reorder projects")
            print("4) Back")
            sub = input("> ").strip()

            if sub == "1":
                self._pick_project_and_edit_info(projects)
                ctx["projects"] = projects
            elif sub == "2":
                self._pick_project_and_edit_bullets(projects)
                ctx["projects"] = projects
            elif sub == "3":
                self._reorder_list_cli(
                    items=projects,
                    label_getter=lambda p: p.get("name", "Project"),
                    title="Reorder Projects",
                )
                ctx["projects"] = projects
            elif sub == "4":
                return
            else:
                print("Invalid selection.")

    def _edit_project_info_cli(self, proj: Dict[str, Any]) -> None:
        print(f"\n--- Edit Project Info: {proj.get('name','Project')} ---")
        for key in ["name", "stack", "dates"]:
            cur = proj.get(key, "") or ""
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

    # -------------------------
    # Education
    # -------------------------

    def _edit_education_menu(self, ctx: Dict[str, Any]) -> None:
        edu: List[Dict[str, Any]] = ctx.get("education", []) or []

        while True:
            print("\n--- Education ---")
            if not edu:
                print("(none)")
            else:
                for i, e in enumerate(edu, 1):
                    school = e.get("school", "")
                    degree = e.get("degree", "")
                    dates = e.get("dates", "")
                    print(f"  {i}) {school} — {degree} ({dates})")

            print("\nOptions:")
            print("  1) Add entry")
            print("  2) Edit entry")
            print("  3) Delete entry")
            print("  4) Reorder entries")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                edu.append(self._prompt_education_entry({}))
                ctx["education"] = edu
            elif sub == "2":
                if not edu:
                    print("No entries to edit.")
                    continue
                n = input("Entry # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(edu):
                    idx = int(n) - 1
                    edu[idx] = self._prompt_education_entry(edu[idx])
                    ctx["education"] = edu
                else:
                    print("Invalid entry number.")
            elif sub == "3":
                if not edu:
                    print("No entries to delete.")
                    continue
                n = input("Entry # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(edu):
                    edu.pop(int(n) - 1)
                    ctx["education"] = edu
                else:
                    print("Invalid entry number.")
            elif sub == "4":
                self._reorder_list_cli(edu, lambda e: e.get("school", "School"), "Reorder Education")
                ctx["education"] = edu
            elif sub == "5":
                return
            else:
                print("Invalid selection.")

    def _prompt_education_entry(self, cur: Dict[str, Any]) -> Dict[str, Any]:
        school = input(f"School [{cur.get('school','')}]: ").strip()
        location = input(f"Location [{cur.get('location','')}]: ").strip()
        degree = input(f"Degree [{cur.get('degree','')}]: ").strip()
        dates = input(f"Dates [{cur.get('dates','')}]: ").strip()

        out = dict(cur)
        if school: out["school"] = school
        if location: out["location"] = location
        if degree: out["degree"] = degree
        if dates: out["dates"] = dates
        return out

    # -------------------------
    # Experience
    # -------------------------

    def _edit_experience_menu(self, ctx: Dict[str, Any]) -> None:
        exp: List[Dict[str, Any]] = ctx.get("experience", []) or []

        while True:
            print("\n--- Experience ---")
            if not exp:
                print("(none)")
            else:
                for i, j in enumerate(exp, 1):
                    title = j.get("title", "")
                    company = j.get("company", "")
                    dates = j.get("dates", "")
                    print(f"  {i}) {title} @ {company} ({dates})")

            print("\nOptions:")
            print("  1) Add job")
            print("  2) Edit job")
            print("  3) Delete job")
            print("  4) Reorder jobs")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                exp.append(self._prompt_experience_entry({}))
                ctx["experience"] = exp
            elif sub == "2":
                if not exp:
                    print("No jobs to edit.")
                    continue
                n = input("Job # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(exp):
                    idx = int(n) - 1
                    exp[idx] = self._prompt_experience_entry(exp[idx])
                    ctx["experience"] = exp
                else:
                    print("Invalid job number.")
            elif sub == "3":
                if not exp:
                    print("No jobs to delete.")
                    continue
                n = input("Job # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(exp):
                    exp.pop(int(n) - 1)
                    ctx["experience"] = exp
                else:
                    print("Invalid job number.")
            elif sub == "4":
                self._reorder_list_cli(exp, lambda j: j.get("title", "Job"), "Reorder Experience")
                ctx["experience"] = exp
            elif sub == "5":
                return
            else:
                print("Invalid selection.")

    def _prompt_experience_entry(self, cur: Dict[str, Any]) -> Dict[str, Any]:
        title = input(f"Title [{cur.get('title','')}]: ").strip()
        company = input(f"Company [{cur.get('company','')}]: ").strip()
        location = input(f"Location [{cur.get('location','')}]: ").strip()
        dates = input(f"Dates [{cur.get('dates','')}]: ").strip()

        bullets = list(cur.get("bullets", []) or [])
        print("\nEdit bullets for this job:")
        self._edit_bullets_cli(f"{cur.get('title','Job')} bullets", bullets)

        out = dict(cur)
        if title: out["title"] = title
        if company: out["company"] = company
        if location: out["location"] = location
        if dates: out["dates"] = dates
        out["bullets"] = bullets
        return out

    # -------------------------
    # Skills
    # -------------------------

    def _edit_skills_menu(self, ctx: Dict[str, Any]) -> None:
        skills: Dict[str, List[str]] = ctx.get("skills", {}) or {}

        while True:
            print("\n--- Technical Skills ---")
            if not skills:
                print("(none)")
            else:
                for k in sorted(skills.keys(), key=lambda s: s.lower()):
                    print(f"  - {k}: {', '.join(skills.get(k, []) or [])}")

            print("\nOptions:")
            print("  1) Add category")
            print("  2) Rename category")
            print("  3) Delete category")
            print("  4) Edit items in a category")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                name = input("New category name: ").strip()
                if name:
                    skills.setdefault(name, [])
                    ctx["skills"] = skills

            elif sub == "2":
                old = input("Category to rename: ").strip()
                if old in skills:
                    new = input(f"Rename '{old}' to: ").strip()
                    if new and new not in skills:
                        skills[new] = skills.pop(old)
                        ctx["skills"] = skills
                else:
                    print("Category not found.")

            elif sub == "3":
                name = input("Category to delete: ").strip()
                if name in skills:
                    del skills[name]
                    ctx["skills"] = skills
                else:
                    print("Category not found.")

            elif sub == "4":
                name = input("Category to edit: ").strip()
                if name not in skills:
                    print("Category not found.")
                    continue
                self._edit_skill_items_cli(name, skills[name])
                ctx["skills"] = skills

            elif sub == "5":
                return
            else:
                print("Invalid selection.")

    def _edit_skill_items_cli(self, category: str, items: List[str]) -> None:
        while True:
            print(f"\n--- {category} ---")
            if not items:
                print("(none)")
            for i, it in enumerate(items, 1):
                print(f"  {i}) {it}")

            print("\nOptions:")
            print("  1) Add item")
            print("  2) Edit item")
            print("  3) Delete item")
            print("  4) Move item up/down")
            print("  5) Back")
            sub = input("> ").strip()

            if sub == "1":
                v = input("New item: ").strip()
                if v:
                    items.append(v)

            elif sub == "2":
                n = input("Item # to edit: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(items):
                    v = input("New text: ").strip()
                    if v:
                        items[int(n) - 1] = v
                else:
                    print("Invalid item number.")

            elif sub == "3":
                n = input("Item # to delete: ").strip()
                if n.isdigit() and 1 <= int(n) <= len(items):
                    items.pop(int(n) - 1)
                else:
                    print("Invalid item number.")

            elif sub == "4":
                n = input("Item # to move: ").strip()
                if not (n.isdigit() and 1 <= int(n) <= len(items)):
                    print("Invalid item number.")
                    continue
                direction = input("u=up, d=down: ").strip().lower()
                i = int(n) - 1
                if direction == "u" and i > 0:
                    items[i - 1], items[i] = items[i], items[i - 1]
                elif direction == "d" and i < len(items) - 1:
                    items[i + 1], items[i] = items[i], items[i + 1]
                else:
                    print("Can't move that way.")

            elif sub == "5":
                return

            else:
                print("Invalid selection.")

    # -------------------------
    # Generic reorder helper
    # -------------------------

    def _reorder_list_cli(self, items: List[Any], label_getter, title: str) -> None:
        """
        Simple reorder UI:
          - type: "from,to" (1-indexed)
          - moves one element to a new position
        """
        if len(items) < 2:
            print("Nothing to reorder.")
            return

        while True:
            print(f"\n--- {title} ---")
            for i, it in enumerate(items, 1):
                print(f"  {i}) {label_getter(it)}")
            print("Enter move as 'from,to' (example: 3,1), or 'q' to stop.")
            raw = input("> ").strip().lower()
            if raw == "q":
                return
            if "," not in raw:
                print("Invalid format.")
                continue
            a, b = [x.strip() for x in raw.split(",", 1)]
            if not (a.isdigit() and b.isdigit()):
                print("Invalid numbers.")
                continue
            frm = int(a) - 1
            to = int(b) - 1
            if not (0 <= frm < len(items) and 0 <= to < len(items)):
                print("Out of range.")
                continue
            item = items.pop(frm)
            items.insert(to, item)
