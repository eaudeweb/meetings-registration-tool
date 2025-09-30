import datetime
import os

from click.testing import CliRunner
from py.path import local

from mrt.manager import cli
from mrt.models import CustomField, CustomFieldValue, db
from testsuite.utils import add_new_meeting

from .factories import CustomFieldFactory, CustomFieldValueFactory, ParticipantFactory


def test_remove_finished_meetings_sensitive_data_and_documents(app, user):
    upload_dir = local(app.config["UPLOADED_CUSTOM_DEST"])
    participant = ParticipantFactory()

    # Create meeting with open registration (not finished)
    meeting_1 = add_new_meeting(app, user)
    passport_field_1 = CustomFieldFactory(
        field_type=CustomField.IMAGE, meeting=meeting_1, slug="passport"
    )
    CustomFieldValueFactory(
        participant=participant, custom_field=passport_field_1, value="passport-1.png"
    )
    with open(str(upload_dir.join("passport-1.png")), "w") as f:
        f.write("test")

    # Create meeting without open registration (finished)
    meeting_2 = add_new_meeting(app, user)
    passport_field_2 = CustomFieldFactory(
        field_type=CustomField.IMAGE, meeting=meeting_2, slug="passport"
    )

    CustomFieldValueFactory(
        participant=participant, custom_field=passport_field_2, value="passport-2.png"
    )
    with open(str(upload_dir.join("passport-2.png")), "w") as f:
        f.write("test")

    meeting_2.online_registration = False
    meeting_2.date_start = datetime.datetime(2020, 1, 1)
    meeting_2.date_end = datetime.datetime(2020, 1, 2)
    db.session.commit()

    assert meeting_1.online_registration is True
    assert meeting_2.online_registration is False

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "remove_finished_meetings_sensitive_data_and_documents",
            "--field-names=passport",
            "--count-only",
        ],
        obj={"app": app},
    )
    assert result.exit_code == 0
    assert (
        "There are 1 custom field values and 1 files on disk to delete\n"
        in result.output
    )

    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 2

    result = runner.invoke(
        cli,
        [
            "remove_finished_meetings_sensitive_data_and_documents",
            "--field-names=passport",
        ],
        obj={"app": app},
    )
    assert result.exit_code == 0

    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 1
    assert os.path.exists(str(upload_dir.join("passport-1.png")))
    assert not os.path.exists(str(upload_dir.join("passport-2.png")))

    remaining_values = CustomFieldValue.query.all()
    assert any(v.value == "passport-1.png" for v in remaining_values)
    assert not any(v.value == "passport-2.png" for v in remaining_values)


def test_delete_ghost_custom_field_value_files(app, user):
    meeting = add_new_meeting(app, user)

    participant = ParticipantFactory()
    default_cf_count = CustomField.query.count()

    field_with_photo = CustomFieldFactory(
        field_type=CustomField.IMAGE, meeting=meeting, slug="profile_photo"
    )
    CustomFieldValueFactory(
        participant=participant, custom_field=field_with_photo, value="photo.png"
    )

    upload_dir = local(app.config["UPLOADED_CUSTOM_DEST"])
    with open(str(upload_dir.join("photo.png")), "w") as f:
        f.write("test")
    with open(str(upload_dir.join("ghost-photo.png")), "w") as f:
        f.write("test")

    assert CustomField.query.count() - default_cf_count == 1
    assert CustomFieldValue.query.count() == 1

    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 2
    assert os.path.exists(str(upload_dir.join("photo.png")))

    # --count-only should not delete anything
    runner = CliRunner()
    result = runner.invoke(
        cli, ["delete_ghost_custom_field_value_files", "--count-only"], obj={"app": app}
    )
    assert result.exit_code == 0

    assert "There are 1 ghost files to delete" in result.output
    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 2
    assert CustomField.query.count() - default_cf_count == 1
    assert CustomFieldValue.query.count() == 1
    assert os.path.exists(str(upload_dir.join("photo.png")))
    assert os.path.exists(str(upload_dir.join("ghost-photo.png")))

    # Without --count-only, the command should delete ghost files
    runner = CliRunner()
    result = runner.invoke(
        cli, ["delete_ghost_custom_field_value_files"], obj={"app": app}
    )
    assert result.exit_code == 0

    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 1
    assert CustomField.query.count() - default_cf_count == 1
    assert CustomFieldValue.query.count() == 1
    assert os.path.exists(str(upload_dir.join("photo.png")))
    assert not os.path.exists(str(upload_dir.join("ghost-photo.png")))


def test_delete_ghost_custom_field_value_objs(app, user):
    meeting = add_new_meeting(app, user)

    participant = ParticipantFactory()
    default_cf_count = CustomField.query.count()

    field_with_photo = CustomFieldFactory(
        field_type=CustomField.IMAGE, meeting=meeting, slug="profile_photo"
    )
    field_without_photo = CustomFieldFactory(
        field_type=CustomField.IMAGE, meeting=meeting, slug="unexisting_profile_photo"
    )

    CustomFieldValueFactory(
        participant=participant, custom_field=field_with_photo, value="photo.png"
    )
    CustomFieldValueFactory(
        participant=participant,
        custom_field=field_without_photo,
        value="unexisting.png",
    )

    upload_dir = local(app.config["UPLOADED_CUSTOM_DEST"])
    with open(str(upload_dir.join("photo.png")), "w") as f:
        f.write("test")

    assert CustomField.query.count() - default_cf_count == 2
    assert CustomFieldValue.query.count() == 2

    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 1
    assert os.path.exists(str(upload_dir.join("photo.png")))

    # --count-only should not delete anything
    runner = CliRunner()
    result = runner.invoke(
        cli, ["delete_ghost_custom_field_value_objs", "--count-only"], obj={"app": app}
    )
    assert result.exit_code == 0

    assert "There are 1 ghost objects to delete" in result.output
    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 1
    assert CustomField.query.count() - default_cf_count == 2
    assert CustomFieldValue.query.count() == 2
    assert os.path.exists(str(upload_dir.join("photo.png")))

    # Without --count-only, the command should delete ghost files
    runner = CliRunner()
    result = runner.invoke(
        cli, ["delete_ghost_custom_field_value_objs"], obj={"app": app}
    )
    assert result.exit_code == 0

    file_count = len(os.listdir(str(upload_dir)))
    assert file_count == 1
    assert CustomField.query.count() - default_cf_count == 2
    assert CustomFieldValue.query.count() == 1
    assert os.path.exists(str(upload_dir.join("photo.png")))
