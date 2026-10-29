from src.utils.image_utils import save_image, delete_image


def apply_avatar_update(record, new_avatar, field_name="avatar_url"):
    """Update avatar on a model without deleting the file when the path is unchanged."""
    current = getattr(record, field_name, None)

    if new_avatar == "" or new_avatar is None:
        if current:
            delete_image(current)
        setattr(record, field_name, None)
        return

    if not isinstance(new_avatar, str):
        return

    saved_url = save_image(new_avatar)
    if saved_url:
        if saved_url != current:
            delete_image(current)
        setattr(record, field_name, saved_url)
        return

    # Existing stored path or short external reference (not base64)
    if len(new_avatar) < 1000 and new_avatar != current:
        delete_image(current)
        setattr(record, field_name, new_avatar)
