from __future__ import annotations

import hashlib

import cappa

from fujin.commands import BaseCommand
from .deploy import Deploy


@cappa.command(help="Redeploy the application to apply code and environment changes")
class Redeploy(BaseCommand):
    def __call__(self):
        deploy = Deploy()
        deploy.build_app()
        local_requirements = hashlib.md5(
            self.config.requirements.read_bytes()
        ).hexdigest()
        with self.app_environment() as conn:
            hook_manager = self.create_hook_manager(conn)
            hook_manager.pre_deploy()
            current_host_version = conn.run(
                "head -n 1 .versions", warn=True, hide=True
            ).stdout.strip()
            try:
                host_requirements = (
                    conn.run(
                        f"md5sum v{current_host_version}/requirements.txt",
                        warn=True,
                        hide=True,
                    )
                    .stdout.strip()
                    .split()[0]
                )
                skip_requirements = host_requirements == local_requirements
            except IndexError:
                skip_requirements = False
            deploy.transfer_files(conn, skip_requirements=skip_requirements)
            if skip_requirements:
                conn.run(
                    f"cp v{current_host_version}/requirements.txt  {deploy.versioned_assets_dir}/requirements.txt "
                )
            deploy.install_project(conn, skip_setup=skip_requirements)
            deploy.release(conn)
            self.create_process_manager(conn).restart_services()
            deploy.update_version_history(conn)
            hook_manager.post_deploy()
            self.stdout.output("[green]Redeployment completed successfully![/green]")
