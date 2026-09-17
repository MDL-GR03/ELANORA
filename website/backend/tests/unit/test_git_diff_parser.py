from app.service.git_diff_parser import parse_name_status


def test_sorts_name_status_lines_and_skips_unexpected_ones() -> None:
    changes = parse_name_status(
        "A\tnew.eaf\nM\tchanged.eaf\nD\told.eaf\nR100\tmoved.eaf\nbroken\n\n"
    )

    assert changes.new_files == ["new.eaf"]
    assert changes.modified_files == ["changed.eaf"]
    assert changes.deleted_files == ["old.eaf"]


def test_empty_output_has_no_changes() -> None:
    changes = parse_name_status("")

    assert (changes.new_files, changes.modified_files, changes.deleted_files) == (
        [],
        [],
        [],
    )
