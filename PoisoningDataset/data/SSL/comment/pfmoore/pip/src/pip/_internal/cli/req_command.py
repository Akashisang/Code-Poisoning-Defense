"""Contains the RequirementCommand base class.

This class is in a separate module so the commands that do not always
need PackageFinder capability don't unnecessarily import the
PackageFinder machinery and all its vendored dependencies, etc.
"""
