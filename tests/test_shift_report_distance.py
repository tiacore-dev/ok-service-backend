from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.database.managers.shift_reports_managers import ShiftReportsManager


class _Query:
    def __init__(self, project):
        self.project = project

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.project


class _Session:
    def __init__(self, project):
        self.project = project

    def query(self, _model):
        return _Query(self.project)


def _project(object_lng=0.01, object_ltd=0.0):
    return SimpleNamespace(
        project_id=uuid4(),
        objects=SimpleNamespace(lng=object_lng, ltd=object_ltd),
    )


def test_fill_missing_distances_calculates_start_and_finish_in_meters():
    project = _project()
    data = {
        "project": project.project_id,
        "lng_start": 0.0,
        "ltd_start": 0.0,
        "lng_end": 0.0,
        "ltd_end": 0.01,
        "distance_start": None,
        "distance_end": None,
    }

    ShiftReportsManager._fill_missing_distances(_Session(project), data)

    assert data["distance_start"] == pytest.approx(1111.95, rel=1e-4)
    assert data["distance_end"] == pytest.approx(1572.53, rel=1e-4)


def test_fill_missing_distances_preserves_passed_values():
    project = _project()
    data = {
        "project": project.project_id,
        "lng_start": 0.0,
        "ltd_start": 0.0,
        "distance_start": 42.5,
    }

    ShiftReportsManager._fill_missing_distances(_Session(project), data)

    assert data["distance_start"] == 42.5


def test_fill_missing_distances_recalculates_when_patch_changes_coordinates():
    project = _project()
    record = SimpleNamespace(
        project=project.project_id,
        lng_start=0.0,
        ltd_start=0.0,
        distance_start=42.5,
    )
    data = {
        "project": None,
        "lng_start": 0.0,
        "ltd_start": 0.01,
        "distance_start": None,
    }

    ShiftReportsManager._fill_missing_distances(_Session(project), data, record)

    assert data["distance_start"] == pytest.approx(1572.53, rel=1e-4)
