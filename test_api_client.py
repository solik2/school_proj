import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from client import api_client

@patch('httpx.post')
def test_register(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {'ok': True})
    result = api_client.register('id1', 'host:1234', 100, 'http://localhost:8000')
    assert result == {'ok': True}
    mock_post.assert_called_once()

@patch('httpx.get')
def test_list_offers(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [{'id': 'peer1', 'free_space': 50, 'endpoint': 'host:1234'}])
    result = api_client.list_offers(1, 'http://localhost:8000')
    assert result[0]['id'] == 'peer1'
    mock_get.assert_called_once()

@patch('httpx.post')
def test_reserve(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {'reservation_id': 'abc'})
    result = api_client.reserve('from', 'to', 10, 'http://localhost:8000')
    assert result['reservation_id'] == 'abc'
    mock_post.assert_called_once()

@patch('httpx.get')
def test_list_requests(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [{'reservation_id': 'abc', 'from_id': 'from', 'amount': 10}])
    result = api_client.list_requests('peer', 'http://localhost:8000')
    assert result[0]['reservation_id'] == 'abc'
    mock_get.assert_called_once()

@patch('httpx.post')
def test_approve_reservation(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {'approved': True})
    result = api_client.approve_reservation('abc', {'secret': 'data'}, 'http://localhost:8000')
    assert result['approved'] is True
    mock_post.assert_called_once()

import asyncio

@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
def test_report_usage(mock_post):
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {'reported': True})

    async def run():
        result = await api_client.report_usage('from', 'to', 123, 'http://localhost:8000')
        assert result['reported'] is True

    asyncio.run(run())
    mock_post.assert_awaited_once_with(
        'http://localhost:8000/report',
        json={'from_id': 'from', 'to_id': 'to', 'bytes_sent': 123}
    )
