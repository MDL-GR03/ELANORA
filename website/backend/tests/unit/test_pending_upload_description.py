from app.crud.pending_upload import build_pending_description


def test_pending_description_reads_the_persisted_upload_shape() -> None:
    assert (
        build_pending_description(
            {
                "upload_data": {
                    "new_files": [],
                    "modified_files": ["elan_files/session.eaf"],
                    "deleted_files": [],
                }
            }
        )
        == "1 modified file"
    )


def test_pending_description_uses_clear_plural_file_counts() -> None:
    assert (
        build_pending_description(
            {
                "new_files": ["one.eaf", "two.eaf"],
                "modified_files": ["three.eaf"],
                "deleted_files": [],
            }
        )
        == "2 new files, 1 modified file"
    )


def test_pending_description_names_a_content_identical_submission() -> None:
    assert build_pending_description({"upload_data": {}}) == (
        "No file changes detected"
    )
