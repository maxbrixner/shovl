import enum


class PathRestriction(str, enum.Enum):
    must_exist = "must_exist"
    must_be_directory = "must_be_directory"
    must_be_file = "must_be_file"
