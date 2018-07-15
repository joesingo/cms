def remove_extension(path, ext):
    """
    Remove an extension from a file path. `ext` should not include '.'
    """
    full_ext = ".{}".format(ext)
    if path.endswith(full_ext):
        return path[:-len(full_ext)]
    return path


def transfer_pages(from_page, to_page):
    """
    Go through child pages of `from_page` and insert under `to_page`
    """
    for child in from_page.iterchildren():
        to_page.add_child(child)
