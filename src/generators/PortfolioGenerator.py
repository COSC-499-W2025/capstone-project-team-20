from datetime import datetime
from typing import Dict, Any, List
from src.models.ReportProject import PortfolioDetails


class PortfolioGenerator:
    """
    Generates structured portfolio entries for projects.
    """

    SCORE_BENCHMARK_MAX = 75.0

    def __init__(
        self,
        metadata: Dict,
        categorized_files: Dict,
        language_share: Dict,
        project: Any,
        language_list: List[str],
    ):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project
        self.language_list = language_list

    def generate_portfolio_details(self) -> PortfolioDetails:
        code_files, doc_files, test_files, _ = self._get_category_counts()
        total_files = self._get_total_files_count()

        days = self._compute_days()
        duration_str = self._format_duration(days)
        langs = self._format_languages()

        team_count = self._resolve_team_count()
        contributor_roles = self._build_contributor_roles()
        role = self._select_project_role(team_count, contributor_roles)

        collaboration_line = (
            f"Built collaboratively by a team of {team_count} developers, following shared Git-based workflows and iterative delivery."
            if team_count > 1
            else "Developed independently with end-to-end ownership across design, implementation, and maintenance."
        )

        success_line = self._build_success_line(team_count)
        evidence_line = self._build_evidence_line(code_files, test_files, doc_files, team_count)

        overview = (
            f"This software project was built using a tech stack of {langs}"
            f"{self._duration_fragment(duration_str)}. "
            f"It follows a modular and maintainable architecture and contains over {total_files} files, "
            f"including {code_files} source modules, {test_files} automated tests, and {doc_files} documentation files. "
            f"{collaboration_line} {success_line} {evidence_line}"
        ).strip()

        key_points = self._build_key_contributions(
            langs=langs,
            code_files=code_files,
            test_files=test_files,
            doc_files=doc_files,
            team_count=team_count,
        )

        project_name = getattr(self.project, "name", "Project")

        return PortfolioDetails(
            project_name=project_name,
            role=role,
            timeline=duration_str,
            technologies=langs,
            overview=overview,
            achievements=key_points,
            contributor_roles=contributor_roles,
        )

    def _score_display(self, score: float) -> str:
        benchmark = self.SCORE_BENCHMARK_MAX
        pct = 0.0 if benchmark <= 0 else max(0.0, min((score / benchmark) * 100.0, 100.0))
        return f"{score:.1f}/{benchmark:.0f} ({pct:.1f}%)"

    def _normalize_counts(self, raw: Dict[str, Any]) -> Dict[str, int]:
        if not isinstance(raw, dict):
            return {}
        nested = raw.get("counts")
        target = nested if isinstance(nested, dict) else raw
        out: Dict[str, int] = {}
        for k, v in target.items():
            if isinstance(v, (int, float)):
                out[str(k).strip().lower()] = int(v or 0)
        return out

    def _sum_aliases(self, counts: Dict[str, int], aliases: List[str]) -> int:
        return int(sum(int(counts.get(a, 0) or 0) for a in aliases))

    def _get_category_counts(self) -> tuple[int, int, int, int]:
        counts = self._normalize_counts(self.categorized_files)

        code_files = self._sum_aliases(counts, ["code", "source", "src", "backend", "frontend", "api"])
        test_files = self._sum_aliases(counts, ["test", "tests", "qa", "spec", "specs"])
        doc_files = self._sum_aliases(counts, ["docs", "doc", "documentation", "readme"])
        config_files = self._sum_aliases(counts, ["config", "configs", "configuration"])

        if code_files == 0 and test_files == 0 and doc_files == 0 and counts:
            code_files = int(counts.get("code", 0) or counts.get("source", 0) or 0)
            test_files = int(counts.get("test", 0) or counts.get("tests", 0) or 0)
            doc_files = int(counts.get("docs", 0) or counts.get("documentation", 0) or 0)

        return code_files, doc_files, test_files, config_files

    def _get_total_files_count(self) -> int:
        counts = self._normalize_counts(self.categorized_files)
        from_counts = sum(v for v in counts.values() if isinstance(v, (int, float)))
        if from_counts > 0:
            return int(from_counts)
        fallback = int(getattr(self.project, "num_files", 0) or 0)
        return max(fallback, 0)

    def _build_key_contributions(
        self,
        langs: str,
        code_files: int,
        test_files: int,
        doc_files: int,
        team_count: int,
    ) -> List[str]:
        points: List[str] = []

        points.append(
            f"Contributed to core features using {langs}, contributing to a codebase of {max(code_files, 1)}+ well-structured source files."
        )

        if test_files > 0 and doc_files > 0:
            points.append(
                f"Produced {doc_files}+ documentation files and implemented {test_files} automated tests, helping maintainability and onboarding."
            )
        elif test_files > 0:
            points.append(
                f"Implemented {test_files} automated tests to improve reliability and reduce regression risk."
            )
        elif doc_files > 0:
            points.append(
                f"Produced {doc_files}+ documentation files to strengthen maintainability and knowledge transfer."
            )
        else:
            points.append("Maintained project structure and implementation quality through modular organization.")

        points.append(self._build_impact_bullet(team_count))
        return points[:3]

    def _build_impact_bullet(self, team_count: int) -> str:
        share = self._safe_float(getattr(self.project, "individual_contributions", {}).get("contribution_share_percent", 0.0))
        commits = self._estimate_commits()
        score = self._safe_float(getattr(self.project, "resume_score", 0.0))

        if team_count > 1 and share > 0:
            if score > 0:
                return (
                    f"Demonstrated measurable impact through {share:.1f}% individual contribution share, "
                    f"{commits} commits delivered, and composite project score of {self._score_display(score)}."
                )
            return (
                f"Demonstrated measurable impact through {share:.1f}% individual contribution share "
                f"and {commits} commits delivered."
            )

        if score > 0:
            return (
                f"Demonstrated measurable impact through composite project score of {self._score_display(score)} "
                f"and sustained ownership of implementation outcomes."
            )

        return "Demonstrated measurable impact through sustained ownership of implementation outcomes."

    def _estimate_commits(self) -> int:
        contribs = getattr(self.project, "author_contributions", []) or []
        total = 0
        for c in contribs:
            try:
                total += int(c.get("total_commits", 0) or 0)
            except Exception:
                continue
        return total

    def _build_success_line(self, team_count: int) -> str:
        share = self._safe_float(getattr(self.project, "individual_contributions", {}).get("contribution_share_percent", 0.0))
        commits = self._estimate_commits()
        score = self._safe_float(getattr(self.project, "resume_score", 0.0))

        if team_count > 1 and share > 0 and commits > 0 and score > 0:
            return (
                f"Evidence of success includes {share:.1f}% individual contribution share, "
                f"{commits} commits delivered, and composite project score of {self._score_display(score)}."
            )
        if commits > 0 and score > 0:
            return f"Evidence of success includes {commits} commits delivered and composite project score of {self._score_display(score)}."
        if score > 0:
            return f"Evidence of success includes a composite project score of {self._score_display(score)}."
        return "Evidence of success includes sustained implementation ownership and delivery consistency."

    def _build_evidence_line(self, code_files: int, test_files: int, doc_files: int, team_count: int) -> str:
        test_ratio = 0.0 if code_files <= 0 else (test_files / max(code_files, 1))
        test_ratio_pct = max(0.0, min(test_ratio * 100.0, 100.0))

        # documentation_habits_score is 0..1 in your system, present as percent.
        doc_score_raw = self._safe_float(getattr(self.project, "documentation_habits_score", 0.0))
        doc_score_pct = max(0.0, min(doc_score_raw * 100.0, 100.0))

        collab_share = self._safe_float(getattr(self.project, "individual_contributions", {}).get("contribution_share_percent", 0.0))

        parts = [f"Skill evidence: Testing: {test_ratio_pct:.0f}% test coverage ratio"]
        if doc_files > 0 and doc_score_raw > 0:
            parts.append(f"Documentation: {doc_score_pct:.0f}% documentation habits score")
        if team_count > 1 and collab_share > 0:
            parts.append(f"Collaboration: {collab_share:.1f}% individual contribution share")

        return "; ".join(parts) + "."

    def _format_languages(self) -> str:
        if self.language_share:
            ordered = sorted(
                self.language_share.items(),
                key=lambda item: self._safe_float(item[1]),
                reverse=True,
            )
            langs = [name for name, _ in ordered if name]
            if langs:
                return ", ".join(langs[:4])

        if self.language_list:
            return ", ".join(self.language_list[:4])

        return "multiple languages"

    def _duration_fragment(self, duration_str: str) -> str:
        if duration_str == "N/A":
            return ""
        return f" over {duration_str}"

    def _safe_float(self, v: Any) -> float:
        try:
            return float(v or 0.0)
        except Exception:
            return 0.0

    def _resolve_team_count(self) -> int:
        # Prefer author_count when present because selected-author views can shrink authors list.
        explicit_author_count = int(getattr(self.project, "author_count", 0) or 0)
        authors = list(getattr(self.project, "authors", []) or [])

        if explicit_author_count > 0:
            return explicit_author_count
        if authors:
            return len(authors)

        status = getattr(self.project, "collaboration_status", "individual")
        status_lower = f"{status}".lower()
        return 2 if status_lower == "collaborative" else 1

    def _compute_days(self) -> int:
        start = self.metadata.get("start_date")
        end = self.metadata.get("end_date")
        if not start or not end:
            return 0
        if isinstance(start, str):
            start = datetime.strptime(start, "%Y-%m-%d")
        if isinstance(end, str):
            end = datetime.strptime(end, "%Y-%m-%d")
        return max((end - start).days, 0)

    def _format_duration(self, days: int) -> str:
        if days <= 0:
            return "N/A"
        if days < 30:
            return f"{days} days"
        months, rem = divmod(days, 30)
        if rem == 0:
            return f"{months} month" + ("s" if months > 1 else "")
        return f"{months} month" + ("s" if months > 1 else "") + f" and {rem} days"

    def _pretty_role(self, role_key: str) -> str:
        if not role_key or role_key in ("role_none", "none"):
            return "None"
        role_key = role_key.replace("role_", "")
        mapping = {
            "devops": "DevOps",
            "qa": "QA",
            "backend": "Backend",
            "frontend": "Frontend",
            "docs": "Documentation",
            "fullstack": "Fullstack",
            "tech_lead": "Tech Lead",
        }
        return mapping.get(role_key, role_key.replace("_", " ").title())

    def _build_contributor_roles(self) -> List[Dict[str, Any]]:
        roles = getattr(self.project, "contributor_roles", {}) or {}
        selected_users = list(getattr(self.project, "authors", []) or [])
        entries: List[Dict[str, Any]] = []

        def _is_noreply_email(v: str) -> bool:
            s = (v or "").strip().lower()
            return "@users.noreply.github.com" in s

        def _name_from_noreply(v: str) -> str:
            # 30375170+mr-sban@users.noreply.github.com -> mr-sban
            s = (v or "").strip()
            if "+" in s and "@users.noreply.github.com" in s:
                try:
                    return s.split("+", 1)[1].split("@", 1)[0]
                except Exception:
                    return s
            return s

        def _normalize(v: str) -> str:
            return (v or "").strip().lower()

        # Build lookup from selected display names/usernames (from author_map pipeline).
        selected_lookup: Dict[str, str] = {}
        for name in selected_users:
            raw = str(name).strip()
            if not raw:
                continue
            selected_lookup[_normalize(raw)] = raw

        role_users = sorted(list(roles.keys())) if roles else []

        if role_users:
            for user in role_users:
                info = roles.get(user) or {}
                role_key = info.get("primary_role", "role_none")
                role_name = self._pretty_role(role_key)
                confidence = float(info.get("confidence", 0.0) or 0.0)

                raw_user = str(user).strip()
                low = _normalize(raw_user)

                # Best effort name resolution:
                # 1) exact selected name match
                pretty_name = selected_lookup.get(low)

                # 2) noreply email -> github handle
                if not pretty_name and _is_noreply_email(raw_user):
                    handle = _name_from_noreply(raw_user)
                    pretty_name = selected_lookup.get(_normalize(handle), handle)

                # 3) common email local-part fallback
                if not pretty_name and "@" in raw_user:
                    local = raw_user.split("@", 1)[0]
                    local = local.split("+", 1)[-1] if "+" in local else local
                    pretty_name = selected_lookup.get(_normalize(local), local)

                # 4) final fallback to raw
                if not pretty_name:
                    pretty_name = raw_user

                entries.append({
                    "name": pretty_name,
                    "role": role_name if role_name != "None" else "",
                    "confidence": confidence,
                    "confidence_pct": int(round(confidence * 100)),
                })
        elif selected_users:
            for user in selected_users:
                entries.append({
                    "name": user,
                    "role": "",
                    "confidence": 0.0,
                    "confidence_pct": 0,
                })

        entries.sort(key=lambda item: item["name"].lower())
        return entries

    def _select_project_role(self, team_count: int, contributor_roles: List[Dict[str, Any]]) -> str:
        if contributor_roles:
            best = sorted(contributor_roles, key=lambda x: float(x.get("confidence", 0.0) or 0.0), reverse=True)[0]
            primary_role = (best.get("role") or "").strip()
            if primary_role:
                if team_count > 1:
                    return f"{primary_role} Contributor (Team of {team_count})"
                return f"{primary_role} Developer"

        roles_map = getattr(self.project, "contributor_roles", {}) or {}
        if roles_map:
            sorted_roles = sorted(
                roles_map.items(),
                key=lambda item: float((item[1] or {}).get("confidence", 0.0) or 0.0),
                reverse=True,
            )
            for _, info in sorted_roles:
                role_name = self._pretty_role((info or {}).get("primary_role", "none"))
                conf = float((info or {}).get("confidence", 0.0) or 0.0)
                if role_name != "None" and conf >= 0.35:
                    if team_count > 1:
                        return f"{role_name} Contributor (Team of {team_count})"
                    return f"{role_name} Developer"

        if team_count > 1:
            return f"Team Contributor (Team of {team_count})"
        return "Solo Developer"