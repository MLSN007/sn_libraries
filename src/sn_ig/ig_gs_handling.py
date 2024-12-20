import logging
import random
from typing import Optional, List, Dict, Any
from google_services import GoogleSheetsHandler
from .ig_utils import IgUtils, get_db_connection
from .ig_client import IgClient
import traceback

logging.basicConfig(level=logging.DEBUG)  # Change level to DEBUG
logger = logging.getLogger(__name__)


class IgGSHandling:
    """Handles Instagram Google Sheets operations."""

    def __init__(self, account_id: str, folder_name: str = "ig JK tests"):
        """
        Initialize the IgGSHandling class.

        Args:
            account_id (str): The Instagram account identifier.
            folder_name (str): The name of the Google Drive folder containing the spreadsheet and media files.
        """
        self.account_id = account_id
        self.folder_name = folder_name
        self.gs_handler = GoogleSheetsHandler(account_id)
        db_path = (
            f"C:/Users/manue/Documents/GitHub007/sn-libraries/data/{account_id}_ig.db"
        )
        self.db_connection = get_db_connection(db_path)
        if not self.db_connection:
            raise Exception("Failed to connect to the database.")
        try:
            self.ig_client = IgClient(account_id)
            self.ig_utils = IgUtils(self.ig_client.client)
        except Exception as e:
            logger.error(f"Error initializing IgClient or IgUtils: {str(e)}")
            raise
        self.spreadsheet_id: Optional[str] = None
        self.folder_id: Optional[str] = None

    def authenticate_and_setup(self) -> bool:
        try:
            self.gs_handler.authenticate()
            logger.info("Authentication successful")

            # Check permissions
            if not self.gs_handler.check_permissions():
                logger.error("Failed to check permissions")
                return False
            logger.info("Permissions check successful")

            # Get folder ID
            self.folder_id = self.gs_handler.get_folder_id(self.folder_name)
            if not self.folder_id:
                logger.error(
                    f"Folder '{self.folder_name}' not found. Please check the folder name and permissions."
                )
                return False
            logger.info(f"Folder ID retrieved: {self.folder_id}")

            spreadsheet_name = f"{self.account_id} IG input table"
            # Find the spreadsheet ID within the folder
            self.spreadsheet_id = self.gs_handler.get_file_id_by_name(
                spreadsheet_name, self.folder_id
            )
            if not self.spreadsheet_id:
                logger.error(
                    f"Spreadsheet '{spreadsheet_name}' not found in folder '{self.folder_name}'"
                )
                return False

            # Set the spreadsheet_id in GoogleSheetsHandler
            self.gs_handler.spreadsheet_id = self.spreadsheet_id

            # Now you can read the spreadsheet data
            spreadsheets = self.gs_handler.read_spreadsheet(
                self.spreadsheet_id,
                "'Ig Origin Data'!A:R",  # Or the actual range you want to read
            )
            logger.info(
                f"Successfully set up with folder ID: {self.folder_id} and spreadsheet ID: {self.spreadsheet_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error during authentication and setup: {str(e)}")
            return False

    def update_location_ids(self):
        """Update location IDs for rows with location_str but no location_id."""
        logger.info("Updating location IDs...")
        try:
            data = self.gs_handler.read_spreadsheet(
                self.spreadsheet_id, "'Ig Origin Data'!A:S"
            )
            if not data:
                logger.error("Failed to read spreadsheet data")
                return False

            header = data[0]
            try:
                location_str_index = header.index("location_str")
                location_id_index = header.index("location_id")
                content_id_index = header.index("content_id")
            except ValueError as e:
                logger.error("Required column not found in header: %s", str(e))
                return False

            location_id_col = self._number_to_column_letter(location_id_index + 1)

            updates = []
            any_failed_searches = False
            for row_index, row in enumerate(data[1:], start=2):
                if row[content_id_index]:  # Skip published content
                    continue

                # Check if location needs updating (has location_str but no location_id)
                if row[location_str_index] and not row[location_id_index]:
                    locations = self.ig_utils.get_top_locations_by_name(
                        row[location_str_index]
                    )
                    if locations:
                        location_id = locations[0].pk
                        updates.append(
                            {
                                "range": f"'Ig Origin Data'!{location_id_col}{row_index}",
                                "values": [[str(location_id)]],
                            }
                        )
                        logger.info(
                            f"Will update location ID for row {row_index}: {location_id}"
                        )
                    else:
                        any_failed_searches = True
                        logger.warning(
                            f"No location found for: {row[location_str_index]}"
                        )

            if updates:
                success = self.gs_handler.batch_update_values(updates)
                if success:
                    logger.info(f"Successfully updated {len(updates)} location IDs")
                else:
                    logger.error("Failed to update location IDs")
                return True
            else:
                if any_failed_searches:
                    logger.warning("No location IDs updated due to search failures")
                else:
                    logger.info("No location IDs needed updating")
                return False

        except Exception as e:
            logger.error(f"Error updating location IDs: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def update_music_track_ids(self):
        """Update music track IDs for rows with music_reference but no music_track_id."""
        logger.info("Updating music track IDs...")
        try:
            data = self.gs_handler.read_spreadsheet(
                self.spreadsheet_id, "'Ig Origin Data'!A:S"
            )
            if not data:
                logger.error("Failed to read spreadsheet data")
                return False

            header = data[0]
            try:
                music_reference_index = header.index("music_reference")
                music_track_id_index = header.index("music_track_id")
                content_id_index = header.index("content_id")
            except ValueError as e:
                logger.error("Required column not found in header: %s", str(e))
                return False

            music_track_id_col = self._number_to_column_letter(music_track_id_index + 1)

            updates = []
            any_failed_searches = False
            for row_index, row in enumerate(data[1:], start=2):
                if row[content_id_index]:  # Skip published content
                    continue

                # Check if music track needs updating (has reference but no track id)
                if row[music_reference_index] and not row[music_track_id_index]:
                    tracks = self.ig_utils.music_search(row[music_reference_index])
                    if tracks:
                        track = random.choice(tracks[:3])
                        music_track_id = track.id
                        updates.append(
                            {
                                "range": f"'Ig Origin Data'!{music_track_id_col}{row_index}",
                                "values": [[str(music_track_id)]],
                            }
                        )
                        logger.info(
                            f"Will update music track ID for row {row_index}: {music_track_id}"
                        )
                    else:
                        any_failed_searches = True
                        logger.warning(
                            f"No tracks found for reference: {row[music_reference_index]}"
                        )

            if updates:
                success = self.gs_handler.batch_update_values(updates)
                if success:
                    logger.info(f"Successfully updated {len(updates)} music track IDs")
                else:
                    logger.error("Failed to update music track IDs")
                return True
            else:
                if any_failed_searches:
                    logger.warning("No music track IDs updated due to search failures")
                else:
                    logger.info("No music track IDs needed updating")
                return False

        except Exception as e:
            logger.error(f"Error updating music track IDs: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def update_media_paths(self):
        """Update media_paths for rows with media_file_names but no media_paths."""
        logger.info("Updating media paths...")
        try:
            data = self.gs_handler.read_spreadsheet(
                self.spreadsheet_id, "'Ig Origin Data'!A:S"
            )
            if not data:
                logger.error("Failed to read spreadsheet data")
                return False

            header = data[0]
            try:
                media_file_names_index = header.index("media_file_names")
                media_paths_index = header.index("media_paths")
                content_id_index = header.index("content_id")
            except ValueError as e:
                logger.error("Required column not found in header: %s", str(e))
                return False

            media_paths_col = self._number_to_column_letter(media_paths_index + 1)

            updates = []
            for row_index, row in enumerate(data[1:], start=2):
                if row[content_id_index]:  # Skip published content
                    continue

                # Check if media paths need updating (has file names but no paths)
                if row[media_file_names_index] and not row[media_paths_index]:
                    file_names = row[media_file_names_index].split(",")
                    file_ids = []
                    for file_name in file_names:
                        file_id = self.gs_handler.get_file_id_by_name(
                            file_name.strip(), self.folder_id
                        )
                        if file_id:
                            file_ids.append(file_id)
                            logger.debug(f"Found ID for {file_name}: {file_id}")
                        else:
                            logger.warning(f"Could not find ID for file: {file_name}")

                    if file_ids:
                        media_paths = ",".join(file_ids)
                        updates.append(
                            {
                                "range": f"'Ig Origin Data'!{media_paths_col}{row_index}",
                                "values": [[media_paths]],
                            }
                        )
                        logger.info(
                            f"Will update media paths for row {row_index}: {media_paths}"
                        )

            if updates:
                success = self.gs_handler.batch_update_values(updates)
                if success:
                    logger.info(f"Successfully updated {len(updates)} media paths")
                else:
                    logger.error("Failed to update media paths")
                return True
            else:
                logger.info("No media paths needed updating")
                return False

        except Exception as e:
            logger.error(f"Error updating media paths: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def sync_google_sheet_with_db(self) -> None:
        """
        Syncs the Google Sheet with the SQLite database by uploading new entries
        and updating the Google Sheet with generated content IDs.
        """
        try:
            # Read all rows from the spreadsheet
            data = self.gs_handler.read_spreadsheet(
                self.spreadsheet_id, "'Ig Origin Data'!A:S"
            )
            if not data:
                logger.error("No data found in spreadsheet")
                return

            # Get header row and find content_id column index
            header = data[0]
            try:
                content_id_index = header.index("content_id")
            except ValueError:
                logger.error("content_id column not found in spreadsheet")
                return

            # Filter rows without content_id
            rows_without_content_id = []
            row_indices = []
            for row_idx, row in enumerate(
                data[1:], start=2
            ):  # Start from 2 to match sheet row numbers
                # Skip rows that are too short or already have content_id
                if len(row) <= content_id_index or row[content_id_index]:
                    continue

                # Create a dictionary with column names as keys
                row_dict = {
                    header[i]: row[i] if i < len(row) else None
                    for i in range(len(header))
                }
                row_dict["row_index"] = row_idx  # Add row index for later reference
                rows_without_content_id.append(row_dict)
                row_indices.append(row_idx)

            if not rows_without_content_id:
                logger.info("No new rows to process")
                return

            # Insert rows into the database and get content_ids
            content_ids = []
            for row in rows_without_content_id:
                content_id = self.insert_into_db(row)
                content_ids.append(content_id)

            # Update Google Sheet with content_ids
            self.update_content_ids(content_ids, row_indices)
            logger.info(f"Processed {len(content_ids)} new rows")

        except Exception as e:
            logger.error(f"Error during sync: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def insert_into_db(self, row: dict) -> int:
        """
        Inserts a row into the SQLite database and returns the generated content_id.

        Args:
            row (dict): A dictionary representing a row from the Google Sheet.

        Returns:
            int: The generated content_id from the database.
        """
        print("INSERTING INTO DB", row, "\n")

        # Process mentions to ensure @ symbol
        mentions = row.get("mentions", "")
        if mentions:
            # Split mentions, add @ if needed, and rejoin
            processed_mentions = " ".join(
                f"@{mention.lstrip('@')}" for mention in mentions.split()
            )
        else:
            processed_mentions = ""

        cursor = self.db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO content (
                content_type, media_type, title, caption, hashtags, mentions, 
                location_id, music_track_id, media_file_names, media_paths, 
                link, publish_date, publish_time, status, gs_row_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("content_type"),
                row.get("media_type"),
                row.get("title"),
                row.get("caption"),
                row.get("hashtags"),
                processed_mentions,  # Use processed mentions instead of raw mentions
                row.get("location_id"),
                row.get("music_track_id"),
                row.get("media_file_names"),
                row.get("media_paths"),
                row.get("link"),
                row.get("publish_date"),
                row.get("publish_time"),
                "pending",  # Set initial status
                row.get("row_index"),  # Add the Google Sheet row number
            ),
        )
        self.db_connection.commit()
        return cursor.lastrowid

    def _number_to_column_letter(self, n: int) -> str:
        """
        Convert a column number to Excel-style column letter (A, B, C, ... Z, AA, AB, etc.)

        Args:
            n (int): The column number (1-based)

        Returns:
            str: The Excel-style column letter
        """
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

    def update_content_ids(
        self, content_ids: List[int], row_indices: List[int], status: str = None
    ) -> None:
        """
        Update content IDs and error messages in the Google Sheet.
        If status is 'failed', also update the error_message from database.

        Args:
            content_ids (List[int]): List of content IDs to update
            row_indices (List[int]): List of corresponding row indices
            status (str, optional): The status being updated ('failed', 'published', etc)
        """
        try:
            # Read header row to find content_id and error_message columns
            header_data = self.gs_handler.read_spreadsheet(
                self.spreadsheet_id, "'Ig Origin Data'!1:1"
            )
            if not header_data:
                logger.error("Could not read header row")
                return

            # Find content_id and error_message column indices
            try:
                content_id_index = header_data[0].index("content_id")
                content_id_col = self._number_to_column_letter(content_id_index + 1)

                # Only get error_message column if status is 'failed'
                if status == "failed":
                    error_msg_index = header_data[0].index("error_message")
                    error_msg_col = self._number_to_column_letter(error_msg_index + 1)
            except ValueError as e:
                logger.error("Required column not found in header: %s", str(e))
                return

            # Prepare batch update data
            batch_data = []
            cursor = self.db_connection.cursor()

            for content_id, row_idx in zip(content_ids, row_indices):
                # Update content_id
                batch_data.append(
                    {
                        "range": f"'Ig Origin Data'!{content_id_col}{row_idx}",
                        "values": [[str(content_id)]],
                    }
                )

                # If status is failed, get error message from database and update it
                if status == "failed":
                    cursor.execute(
                        "SELECT error_message FROM content WHERE content_id = ?",
                        (content_id,),
                    )
                    result = cursor.fetchone()
                    if result and result[0]:  # If error message exists
                        batch_data.append(
                            {
                                "range": f"'Ig Origin Data'!{error_msg_col}{row_idx}",
                                "values": [[result[0]]],
                            }
                        )
                        logger.info(
                            f"Adding error message update for content_id {content_id}"
                        )

            if batch_data:
                success = self.gs_handler.batch_update_values(batch_data)
                if success:
                    logger.info(
                        f"Successfully updated {len(content_ids)} rows in Google Sheet"
                    )
                else:
                    logger.error("Failed to update Google Sheet")

        except Exception as e:
            logger.error(f"Error updating content IDs and error messages: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def get_folder_id(self, folder_name: str) -> Optional[str]:
        """Delegate to GoogleSheetsHandler."""
        return self.gs_handler.get_folder_id(folder_name)

    def get_file_id_by_name(
        self, file_name: str, folder_id: Optional[str] = None
    ) -> Optional[str]:
        """Delegate to GoogleSheetsHandler."""
        return self.gs_handler.get_file_id_by_name(file_name, folder_id)

    def get_media(self, file_id: str) -> Optional[bytes]:
        """Delegate to GoogleSheetsHandler."""
        return self.gs_handler.get_media(file_id)

    def get(self, file_id: str, fields: str) -> Optional[Dict[str, Any]]:
        """Delegate to GoogleSheetsHandler."""
        return self.gs_handler.get(file_id, fields)

    def verify_file_exists(self, file_id: str) -> bool:
        """Delegate to GoogleSheetsHandler."""
        return self.gs_handler.verify_file_exists(file_id)

    def authenticate(self) -> bool:
        """Delegate to GoogleSheetsHandler."""
        return self.gs_handler.authenticate()
