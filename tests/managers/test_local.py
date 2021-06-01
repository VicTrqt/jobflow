def test_simple_job(mongo_jobstore, clean_dir, simple_job, capsys):
    from jobflow import run_locally

    # run with log
    job = simple_job("12345")
    uuid = job.uuid
    responses = run_locally(job, store=mongo_jobstore)

    # check responses has been filled
    assert responses[uuid][1].output == "12345_end"

    # check store has the activity output
    result = mongo_jobstore.query_one({"uuid": uuid})
    assert result["output"] == "12345_end"


def test_simple_flow(mongo_jobstore, clean_dir, simple_flow, capsys):
    from pathlib import Path

    from jobflow import run_locally

    flow = simple_flow()
    uuid = flow.jobs[0].uuid

    # run without log
    run_locally(flow, store=mongo_jobstore, log=False)
    captured = capsys.readouterr()
    assert "INFO Started executing jobs locally" not in captured.out
    assert "INFO Finished executing jobs locally" not in captured.out

    # run with log
    responses = run_locally(flow, store=mongo_jobstore)

    # check responses has been filled
    assert responses[uuid][1].output == "12345_end"

    # check store has the activity output
    result = mongo_jobstore.query_one({"uuid": uuid})
    assert result["output"] == "12345_end"

    # check no folders were written
    folders = list(Path(".").glob("job_*/"))
    assert len(folders) == 0

    # check logs printed
    captured = capsys.readouterr()
    assert "INFO Started executing jobs locally" in captured.out
    assert "INFO Finished executing jobs locally" in captured.out

    # run with folders
    responses = run_locally(flow, store=mongo_jobstore, create_folders=True)
    assert responses[uuid][1].output == "12345_end"
    folders = list(Path(".").glob("job_*/"))
    assert len(folders) == 1


def test_connected_flow(mongo_jobstore, clean_dir, connected_flow, capsys):
    from jobflow import run_locally

    flow = connected_flow()
    uuid1 = flow.jobs[0].uuid
    uuid2 = flow.jobs[1].uuid

    # run with log
    responses = run_locally(flow, store=mongo_jobstore)

    # check responses has been filled
    assert len(responses) == 2
    assert responses[uuid1][1].output == "12345_end"
    assert responses[uuid2][1].output == "12345_end_end"

    # check store has the activity output
    result1 = mongo_jobstore.query_one({"uuid": uuid1})
    result2 = mongo_jobstore.query_one({"uuid": uuid2})

    assert result1["output"] == "12345_end"
    assert result2["output"] == "12345_end_end"


def test_nested_flow(mongo_jobstore, clean_dir, nested_flow, capsys):
    from jobflow import run_locally

    flow = nested_flow()
    uuid1 = flow.jobs[0].jobs[0].uuid
    uuid2 = flow.jobs[0].jobs[1].uuid
    uuid3 = flow.jobs[1].jobs[0].uuid
    uuid4 = flow.jobs[1].jobs[1].uuid

    # run with log
    responses = run_locally(flow, store=mongo_jobstore)

    # check responses has been filled
    assert len(responses) == 4
    assert responses[uuid1][1].output == "12345_end"
    assert responses[uuid2][1].output == "12345_end_end"
    assert responses[uuid3][1].output == "12345_end_end_end"
    assert responses[uuid4][1].output == "12345_end_end_end_end"

    # check store has the activity output
    result1 = mongo_jobstore.query_one({"uuid": uuid1})
    result2 = mongo_jobstore.query_one({"uuid": uuid2})
    result3 = mongo_jobstore.query_one({"uuid": uuid3})
    result4 = mongo_jobstore.query_one({"uuid": uuid4})

    assert result1["output"] == "12345_end"
    assert result2["output"] == "12345_end_end"
    assert result3["output"] == "12345_end_end_end"
    assert result4["output"] == "12345_end_end_end_end"


def test_addition_flow(mongo_jobstore, clean_dir, addition_flow, capsys):
    from jobflow import run_locally

    flow = addition_flow()
    uuid1 = flow.jobs[0].uuid

    # run with log
    responses = run_locally(flow, store=mongo_jobstore)
    uuid2 = [u for u in responses.keys() if u != uuid1][0]

    # check responses has been filled
    assert len(responses) == 2
    assert responses[uuid1][1].output == 11
    assert responses[uuid1][1].addition is not None
    assert responses[uuid2][1].output == "11_end"

    # check store has the activity output
    result1 = mongo_jobstore.query_one({"uuid": uuid1})
    result2 = mongo_jobstore.query_one({"uuid": uuid2})

    assert result1["output"] == 11
    assert result2["output"] == "11_end"


def test_detour_flow(mongo_jobstore, clean_dir, detour_flow, capsys):
    from jobflow import run_locally

    flow = detour_flow()
    uuid1 = flow.jobs[0].uuid
    uuid3 = flow.jobs[1].uuid

    # run with log
    responses = run_locally(flow, store=mongo_jobstore)
    uuid2 = [u for u in responses.keys() if u != uuid1 and u != uuid3][0]

    # check responses has been filled
    assert len(responses) == 3
    assert responses[uuid1][1].output == 11
    assert responses[uuid1][1].detour is not None
    assert responses[uuid2][1].output == "11_end"
    assert responses[uuid3][1].output == "12345_end"

    # check store has the activity output
    result1 = mongo_jobstore.query_one({"uuid": uuid1})
    result2 = mongo_jobstore.query_one({"uuid": uuid2})
    result3 = mongo_jobstore.query_one({"uuid": uuid3})

    assert result1["output"] == 11
    assert result2["output"] == "11_end"
    assert result3["output"] == "12345_end"

    # assert job2 (detoured job) ran before job3
    assert result2["completed_at"] < result3["completed_at"]


def test_replace_flow(mongo_jobstore, clean_dir, replace_flow, capsys):
    from jobflow import run_locally

    flow = replace_flow()
    uuid1 = flow.jobs[0].uuid
    uuid2 = flow.jobs[1].uuid

    # run with log
    responses = run_locally(flow, store=mongo_jobstore)

    # check responses has been filled
    assert len(responses) == 2
    assert len(responses[uuid1]) == 2
    assert responses[uuid1][1].output == 11
    assert responses[uuid1][1].replace is not None
    assert responses[uuid1][2].output == "11_end"
    assert responses[uuid2][1].output == "12345_end"

    # check store has the activity output
    result1 = mongo_jobstore.query_one({"uuid": uuid1, "index": 1})
    result2 = mongo_jobstore.query_one({"uuid": uuid1, "index": 2})
    result3 = mongo_jobstore.query_one({"uuid": uuid2, "index": 1})

    assert result1["output"] == 11
    assert result2["output"] == "11_end"
    assert result3["output"] == "12345_end"

    # assert job2 (detoured job) ran before job3
    assert result2["completed_at"] < result3["completed_at"]
