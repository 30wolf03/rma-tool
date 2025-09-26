#!/usr/bin/env python3
"""
Git-based Auto-Updater for RMA-Tool
Automatically checks for and applies updates from Git repository
"""

import subprocess
import sys
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass

from shared.utils.logger import LogBlock, setup_logger

# Optional GUI imports (only when needed)
try:
    from shared.utils.enhanced_logging import LoggingMessageBox, get_module_logger
    GUI_AVAILABLE = True
except ImportError:
    # Fallback when PySide6 is not available
    GUI_AVAILABLE = False
    get_module_logger = lambda name: setup_logger(f"GitUpdater.{name}")
    LoggingMessageBox = None


@dataclass
class UpdateInfo:
    """Information about available updates"""
    has_updates: bool
    current_commit: str
    remote_commit: str
    commits_behind: int
    changelog: List[str]


class GitUpdater:
    """Handles Git-based updates for the RMA-Tool"""

    def __init__(self, parent_widget=None):
        self.logger = get_module_logger("GitUpdater")
        self.parent_widget = parent_widget

        # Find the actual project root (not the executable location)
        if getattr(sys, "frozen", False):
            # When running as executable, look for the original project location
            # This is a heuristic - in a real deployment, you'd configure this properly
            executable_path = Path(sys.executable).parent
            # Try to find the project root by looking for common indicators
            if (executable_path / ".git").exists():
                self.repo_path = executable_path
            else:
                # Fallback: assume the executable is in a subdirectory of the project
                self.repo_path = executable_path.parent.parent.parent
        else:
            # Development mode
            self.repo_path = Path(__file__).parent.parent.parent

        self.logger.info(f"GitUpdater initialized - frozen: {getattr(sys, 'frozen', False)}")
        self.logger.info(f"Executable path: {sys.executable}")
        self.logger.info(f"Repository path: {self.repo_path}")
        self.logger.info(f"Git exists: {(self.repo_path / '.git').exists()}")

        with LogBlock(self.logger, logging.INFO) as log:
            log(f"Updater initialisiert für Repository: {self.repo_path}")

    def _run_git_command(self, command: List[str], check: bool = True) -> Tuple[bool, str]:
        """Execute git command safely"""
        try:
            result = subprocess.run(
                ['git'] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
                # Prevent console window creation on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if check and result.returncode != 0:
                self.logger.error(f"Git command failed: {' '.join(command)}")
                self.logger.error(f"Error: {result.stderr}")
                return False, result.stderr

            return True, result.stdout.strip()

        except subprocess.TimeoutExpired:
            self.logger.error(f"Git command timed out: {' '.join(command)}")
            return False, "Command timed out"
        except Exception as e:
            self.logger.error(f"Git command error: {str(e)}")
            return False, str(e)

    def is_git_repository(self) -> bool:
        """Check if current directory is a git repository"""
        success, _ = self._run_git_command(['rev-parse', '--git-dir'], check=False)
        return success

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash"""
        success, output = self._run_git_command(['rev-parse', 'HEAD'])
        return output if success else None

    def get_remote_commit(self) -> Optional[str]:
        """Get latest remote commit hash"""
        # Fetch latest changes from both remotes
        self._run_git_command(['fetch', 'origin'], check=False)
        self._run_git_command(['fetch', 'backup'], check=False)

        # Try backup remote first (primary), then origin (fallback)
        success, output = self._run_git_command(['rev-parse', 'backup/master'])
        if not success:
            success, output = self._run_git_command(['rev-parse', 'origin/master'])

        return output if success else None

    def get_commits_behind(self) -> int:
        """Get number of commits behind remote"""
        # Try backup remote first (primary), then origin (fallback)
        success, output = self._run_git_command(['rev-list', '--count', 'HEAD..backup/master'])
        if not success:
            success, output = self._run_git_command(['rev-list', '--count', 'HEAD..origin/master'])

        try:
            return int(output) if success else 0
        except ValueError:
            return 0

    def get_changelog(self, max_commits: int = 10) -> List[str]:
        """Get recent commit messages"""
        # Try backup remote first (primary), then origin (fallback)
        success, output = self._run_git_command([
            'log', f'-{max_commits}', '--oneline', 'HEAD..backup/master'
        ])

        if not success:
            success, output = self._run_git_command([
                'log', f'-{max_commits}', '--oneline', 'HEAD..origin/master'
            ])

        return output.split('\n') if success and output else []

    def check_for_updates(self) -> UpdateInfo:
        """Check if updates are available"""
        self.logger.info("=== STARTING UPDATE CHECK ===")
        with LogBlock(self.logger, logging.INFO) as log:
            log("Prüfe auf verfügbare Updates...")

            # Check if git repository exists
            self.logger.info(f"Checking if git repository exists at: {self.repo_path}")
            if not self.is_git_repository():
                self.logger.error("Kein Git-Repository gefunden")
                return UpdateInfo(False, "", "", 0, [])

            self.logger.info("Git repository found, getting current commit...")
            current = self.get_current_commit()
            if not current:
                self.logger.error("Could not get current commit")
                return UpdateInfo(False, "", "", 0, [])

            self.logger.info(f"Current commit: {current}")

            self.logger.info("Getting remote commit...")
            remote = self.get_remote_commit()
            if not remote:
                self.logger.error("Could not get remote commit")
                return UpdateInfo(False, current, "", 0, [])

            self.logger.info(f"Remote commit: {remote}")

            self.logger.info("Getting commits behind...")
            behind = self.get_commits_behind()
            self.logger.info(f"Commits behind: {behind}")

            self.logger.info("Getting changelog...")
            changelog = self.get_changelog()
            self.logger.info(f"Changelog entries: {len(changelog)}")

            has_updates = behind > 0

            log(f"Aktuelle Commit: {current}")
            log(f"Remote Commit: {remote}")
            log(f"Commits hinterher: {behind}")

            self.logger.info(f"=== UPDATE CHECK COMPLETE - Updates available: {has_updates} ===")
            return UpdateInfo(has_updates, current, remote, behind, changelog)

    def perform_update(self, backup: bool = True) -> Tuple[bool, str]:
        """Perform the actual update"""
        with LogBlock(self.logger, logging.INFO) as log:
            log("Starte Update-Prozess...")

            # Create backup if requested
            if backup:
                backup_path = self._create_backup()
                if backup_path:
                    log(f"Backup erstellt: {backup_path}")
                else:
                    log("Backup konnte nicht erstellt werden")

            try:
                # Reset any local changes
                success, _ = self._run_git_command(['reset', '--hard', 'HEAD'])
                if not success:
                    return False, "Konnte lokale Änderungen nicht zurücksetzen"

                # Pull latest changes (try backup first, then origin)
                success, output = self._run_git_command(['pull', 'backup', 'master'])
                if not success:
                    success, output = self._run_git_command(['pull', 'origin', 'master'])

                if success:
                    log("Update erfolgreich durchgeführt")
                    return True, "Update erfolgreich installiert"
                else:
                    return False, f"Update fehlgeschlagen: {output}"

            except Exception as e:
                self.logger.error(f"Update-Fehler: {str(e)}")
                return False, f"Update-Fehler: {str(e)}"

    def _create_backup(self) -> Optional[Path]:
        """Create a backup of current state"""
        try:
            backup_dir = self.repo_path / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = subprocess.run(
                ['git', 'log', '-1', '--format=%cd', '--date=short'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                # Prevent console window creation on Windows
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            ).stdout.strip().replace('-', '')

            commit = self.get_current_commit()[:8] if self.get_current_commit() else "unknown"

            backup_name = f"backup_{timestamp}_{commit}.zip"
            backup_path = backup_dir / backup_name

            # Create backup using git archive
            archive_success, _ = self._run_git_command([
                'archive', '--format=zip', '--output', str(backup_path), 'HEAD'
            ])

            return backup_path if archive_success else None

        except Exception as e:
            self.logger.error(f"Backup-Fehler: {str(e)}")
            return None

    def show_update_notification(self, update_info: UpdateInfo):
        """Show update notification to user"""
        if not update_info.has_updates:
            return

        message = "Update verfügbar!\n\n"
        message += f"Neue Commits: {update_info.commits_behind}\n\n"
        message += "Änderungen:\n" + "\n".join(f"• {commit}" for commit in update_info.changelog[:5])

        if len(update_info.changelog) > 5:
            message += f"\n... und {len(update_info.changelog) - 5} weitere"

        try:
            if GUI_AVAILABLE and self.parent_widget:
                reply = LoggingMessageBox.question(
                    self.parent_widget,
                    "Update verfügbar",
                    message + "\n\nJetzt aktualisieren?",
                    LoggingMessageBox.StandardButton.Yes | LoggingMessageBox.StandardButton.No
                )
                return reply == LoggingMessageBox.StandardButton.Yes
            else:
                print(f"\n=== UPDATE VERFÜGBAR ===\n{message}\n")
                response = input("Jetzt aktualisieren? (j/n): ").lower().strip()
                return response in ['j', 'ja', 'yes', 'y']
        except Exception as e:
            self.logger.error(f"Fehler bei Update-Benachrichtigung: {str(e)}")
            return False


def check_and_update_on_startup(parent_widget=None, auto_update: bool = False) -> bool:
    """Check for updates on startup and optionally update automatically
    DEPRECATED: This function is no longer used. Updates are now user-triggered only.
    """
    # This function is deprecated - updates are now handled manually only
    return True  # Always continue normally