def test_shift_report_swagger_models_are_registered(test_app):
    response = test_app.test_client().get("/swagger.json")

    assert response.status_code == 200
    definitions = response.json["definitions"]
    assert "ShiftReportUser" in definitions
    assert "ShiftReportUpdater" in definitions
