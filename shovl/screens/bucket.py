import copy
import logging
import pathlib
from typing import Optional

from rich.text import Text
from textual.widgets import DataTable

import shovl.schemas as schemas
import shovl.screens as screens
import shovl.services as services
from shovl.providers.bucket import BucketProvider

from .path import PathScreen
from .service import ServiceScreen

logger = logging.getLogger("shovl.screens.bucket")


class BucketScreen(ServiceScreen):
    """
    Screen to browse the contents of a S3 bucket.
    """

    BINDINGS = [
        ("backspace", "back", "back"),
        ("f", "filter", "filter"),
        ("d", "download", "download"),
        ("u", "upload", "upload"),
        ("x", "delete", "delete"),
    ]

    ### Actions ###

    def action_download(self) -> None:
        """
        Download the selected bucket entity.
        """
        entity = self.get_selected_row()

        assert isinstance(entity, schemas.BucketEntity)

        if entity and entity.type in (
            schemas.BucketEntityType.file,
            schemas.BucketEntityType.folder,
        ):

            def callback(path: pathlib.Path | None) -> None:
                if path:
                    self.run_in_thread(
                        target=self.download_worker,
                        name="DownloadWorker",
                        entity=entity,
                        target_path=path,
                    )

            self.app.push_screen(
                PathScreen(
                    label="Enter local target directory:",
                    restrictions=[schemas.PathRestriction.must_be_directory],
                ),
                callback=callback,
            )
        else:
            self.notify_info("Only files and folders can be downloaded.")

    def action_upload(self) -> None:
        """
        Upload a local file or directory to the selected bucket or folder.
        """
        entity = self.current_entity

        assert isinstance(entity, schemas.BucketEntity)

        if entity and entity.type in (
            schemas.BucketEntityType.bucket,
            schemas.BucketEntityType.folder,
        ):

            def callback(path: pathlib.Path | None) -> None:
                if path:
                    self.run_in_thread(
                        target=self.upload_worker,
                        name="UploadWorker",
                        entity=entity,
                        source_path=path,
                    )

            self.app.push_screen(
                PathScreen(
                    label="Enter local source file or directory:",
                    restrictions=[schemas.PathRestriction.must_exist],
                ),
                callback=callback,
            )
        else:
            self.notify_info(
                "Please select an S3 bucket or folder as a target."
            )

    def action_delete(self) -> None:
        """
        Delete the selected bucket entity.
        """
        entity = self.get_selected_row()

        assert isinstance(entity, schemas.BucketEntity)

        short_path = pathlib.Path(entity.name).name

        self.app.push_screen(
            screens.ConfirmScreen(
                label=f"Are you sure you want to delete '{short_path}'?",
            ),
            callback=self.confirm_delete,
        )

    ### Event handlers ###

    def on_mount(self) -> None:
        """
        Handle the screen mount event by initializing the table, i.e. listing
        the root bucket contents.
        """
        self.run_in_thread(
            target=self.inspection_worker,
            name="InspectionWorker",
            entity=schemas.BucketEntity(
                name="",
                type=schemas.BucketEntityType.bucket,
            ),
            add_current_to_history=False,
        )

    def on_data_table_cell_selected(
        self, event: DataTable.CellSelected
    ) -> None:
        """
        Handle Enter key on list items.
        """
        entity = self.get_selected_row()

        assert isinstance(entity, schemas.BucketEntity)

        if entity and entity.type == schemas.BucketEntityType.folder:
            self.run_in_thread(
                target=self.inspection_worker,
                name="InspectionWorker",
                entity=entity,
                add_current_to_history=True,
            )

    ### Class methods ###

    def inspect(
        self, entity: schemas.ServiceEntity, add_current_to_history: bool
    ) -> None:
        """
        Inspect a specific row in the table. This method is meant to be
        called from a separate thread to avoid blocking the UI.
        """
        assert isinstance(entity, schemas.BucketEntity)
        assert isinstance(self.provider, BucketProvider)

        match entity.type:
            case schemas.BucketEntityType.bucket:
                entities = self.provider.inspect(prefix=None)
            case schemas.BucketEntityType.folder:
                entities = self.provider.inspect(prefix=entity.name)
            case _:
                raise Exception(f"Unsupported entity type: {entity.type}")

        self.all_entities = entities
        self.filtered_entities = copy.copy(self.all_entities)

        if self.current_entity and add_current_to_history:
            self.add_to_history()

        self.current_filter = ""

        self.current_entity = entity

    def download(
        self, entity: schemas.BucketEntity, target_path: pathlib.Path
    ) -> None:
        """
        Download a specific bucket entity. Meant to be called from a separate
        thread to avoid blocking the UI.
        """
        assert isinstance(self.provider, BucketProvider)

        if entity.type not in (
            schemas.BucketEntityType.file,
            schemas.BucketEntityType.folder,
        ):
            raise Exception("Only files and folders can be downloaded.")

        self.provider.download(
            key=entity.name,
            target=target_path,
            progress_callback=self.download_progress_callback,
        )

    def upload(
        self, entity: schemas.BucketEntity, source_path: pathlib.Path
    ) -> None:
        """
        Upload local files to bucket. Meant to be called from a separate
        thread to avoid blocking the UI.
        """
        assert isinstance(self.provider, BucketProvider)

        if entity.type not in (
            schemas.BucketEntityType.bucket,
            schemas.BucketEntityType.folder,
        ):
            raise Exception("Only buckets and folders can be upload targets.")

        self.provider.upload(
            key=entity.name,
            source=source_path,
            progress_callback=self.upload_progress_callback,
        )

    def confirm_delete(self, confirmed: Optional[bool] = False) -> None:
        """
        Callback function for delete confirmation screen.
        """
        if not confirmed:
            return

        entity = self.get_selected_row()

        assert isinstance(entity, schemas.BucketEntity)

        if entity and entity.type in (
            schemas.BucketEntityType.file,
            schemas.BucketEntityType.folder,
        ):
            self.run_in_thread(
                target=self.delete_worker,
                name="DeleteWorker",
                entity=entity,
            )
        else:
            self.notify_info("Only files and folders can be deleted.")

    def delete(self, entity: schemas.BucketEntity) -> None:
        """
        Upload local files to bucket. Meant to be called from a separate
        thread to avoid blocking the UI.
        """
        assert isinstance(self.provider, BucketProvider)

        if entity.type not in (
            schemas.BucketEntityType.folder,
            schemas.BucketEntityType.file,
        ):
            raise Exception("Only folders and files can be deleted.")

        self.provider.delete(
            key=entity.name,
            progress_callback=self.delete_progress_callback,
        )

    def filter_view(self) -> None:
        """
        Filter bucket entities based on filter query. Meant to
        be called from a separate thread to avoid blocking the UI.
        """
        query = self.current_filter.lower().strip()

        if not query:
            self.filtered_entities = copy.copy(self.all_entities)
        else:
            self.filtered_entities = [
                entity
                for entity in self.all_entities
                if (query in entity.name.lower())
            ]

    def add_columns(self, entity: schemas.ServiceEntity) -> None:
        """
        Add columns to the table based on the type of entity.
        """
        self.table.add_columns("Name", "Size", "Last Modified", "Type")

    def add_row(self, entity: schemas.ServiceEntity) -> None:
        """
        Add a row to the table.
        """
        assert isinstance(entity, schemas.BucketEntity)

        name = self.get_entity_display_name(entity=entity)

        size = services.format_file_size(entity.size) if entity.size else ""
        last_modified = (
            services.to_time_string(entity.last_modified)
            if entity.last_modified
            else ""
        )

        primary_color = self.app.theme_variables.get("primary")

        self.table.add_row(
            Text(
                name,
                style=f"bold {primary_color}"
                if entity.type
                in (
                    schemas.BucketEntityType.folder,
                    schemas.BucketEntityType.bucket,
                )
                else "",
            ),
            size,
            last_modified,
            entity.type.value,
        )

    def get_entity_display_name(self, entity: schemas.BucketEntity) -> str:
        """
        Get the display name for a bucket entity.
        """
        return pathlib.Path(entity.name).name

    ### Callbacks ###

    def download_progress_callback(self, current: int, total: int) -> None:
        """
        Callback function to update the status screen with download progress.
        """
        self.app.call_from_thread(
            lambda: (
                self.status_screen.update_label(
                    f"Downloading file {current}/{total}..."
                )
                if self.status_screen
                else None
            )
        )

    def upload_progress_callback(self, current: int, total: int) -> None:
        """
        Callback function to update the status screen with upload progress.
        """
        self.app.call_from_thread(
            lambda: (
                self.status_screen.update_label(
                    f"Uploading file {current}/{total}..."
                )
                if self.status_screen
                else None
            )
        )

    def delete_progress_callback(self, current: int, total: int) -> None:
        """
        Callback function to update the status screen with delete progress.
        """
        self.app.call_from_thread(
            lambda: (
                self.status_screen.update_label(
                    f"Deleting file {current}/{total}..."
                )
                if self.status_screen
                else None
            )
        )

    def abort_callback(self) -> None:
        """
        Callback function to abort the current operation. Not implemented yet.
        """
        self.provider.abort_current_operation()

        self.notify_info("Operation aborted by user.")

    ### Workers ###

    def download_worker(
        self, entity: schemas.BucketEntity, target_path: pathlib.Path
    ) -> None:
        """
        Download an entity.
        """
        try:
            self.app.call_from_thread(
                self.push_status_screen,
                label="Preparing download...",
                abort_callback=self.abort_callback,
            )

            self.download(entity=entity, target_path=target_path)

            self.app.call_from_thread(self.dismiss_status_screen)

            self.app.call_from_thread(
                lambda: self.notify_info(
                    f"Download of '{entity.name}' completed."
                )
            )
        except Exception as exception:
            logger.exception(f"Download failed: {exception}")
            self.app.call_from_thread(self.dismiss_status_screen)
            self.app.call_from_thread(self.focus_view)
            message = str(exception)
            self.app.call_from_thread(
                lambda: self.notify_error(f"Download failed: {message}")
            )

    def upload_worker(
        self, entity: schemas.BucketEntity, source_path: pathlib.Path
    ) -> None:
        """
        Upload a path.
        """
        try:
            self.app.call_from_thread(
                self.push_status_screen,
                label="Preparing upload...",
                abort_callback=self.abort_callback,
            )

            self.upload(entity=entity, source_path=source_path)

            if self.current_entity:
                self.inspect(
                    entity=self.current_entity, add_current_to_history=False
                )
                self.app.call_from_thread(
                    self.refresh_view, show_truncated_hint=False
                )

            self.app.call_from_thread(self.dismiss_status_screen)

            self.app.call_from_thread(
                lambda: self.notify_info(
                    f"Upload of '{source_path}' completed."
                )
            )
        except Exception as exception:
            logger.exception(f"Upload failed: {exception}")
            self.app.call_from_thread(self.dismiss_status_screen)
            self.app.call_from_thread(self.focus_view)
            message = str(exception)
            self.app.call_from_thread(
                lambda: self.notify_error(f"Upload failed: {message}")
            )

    def delete_worker(self, entity: schemas.BucketEntity) -> None:
        """
        Delete a path.
        """
        try:
            self.app.call_from_thread(
                self.push_status_screen,
                label="Preparing deletion...",
                abort_callback=self.abort_callback,
            )

            self.delete(entity=entity)

            if self.current_entity:
                self.inspect(
                    entity=self.current_entity, add_current_to_history=False
                )
                self.app.call_from_thread(
                    self.refresh_view, show_truncated_hint=False
                )

            self.app.call_from_thread(self.dismiss_status_screen)

            self.app.call_from_thread(
                lambda: self.notify_info(
                    f"Deletion of '{entity.name}' completed."
                )
            )
        except Exception as exception:
            logger.exception(f"Deletion failed: {exception}")
            self.app.call_from_thread(self.dismiss_status_screen)
            self.app.call_from_thread(self.focus_view)
            message = str(exception)
            self.app.call_from_thread(
                lambda: self.notify_error(f"Deletion failed: {message}")
            )
