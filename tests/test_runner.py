from app.agents.tools import ParseTransactionQuestionTool


async def test_parse_transaction_question_extracts_failed_last_two_days():
    tool = ParseTransactionQuestionTool()
    result = await tool(None, {"question": "Give transactions failed in the last 2 days"})

    assert result == {"status": "error", "days": 2}


async def test_parse_transaction_question_extracts_today():
    tool = ParseTransactionQuestionTool()
    result = await tool(None, {"question": "Show failed transactions today"})

    assert result == {"status": "error", "days": 1}


async def test_parse_transaction_question_extracts_success_last_five_days():
    tool = ParseTransactionQuestionTool()
    result = await tool(None, {"question": "Show successful transactions in the last 5 days"})

    assert result == {"status": "passed", "days": 5}


async def test_parse_transaction_question_extracts_failed_last_ten_days():
    tool = ParseTransactionQuestionTool()
    result = await tool(None, {"question": "Show failed transactions in the last10 days"})

    assert result == {"status": "error", "days": 10}
