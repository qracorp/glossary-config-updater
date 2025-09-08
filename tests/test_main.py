"""
Tests for main module (GlossaryUpdater class)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from glossary_updater.main import GlossaryUpdater, GlossaryUpdaterError
from glossary_updater.api_client import AuthenticationError, ConfigurationError
from glossary_updater.processor import ProcessingError, GlossaryTerm
from glossary_updater.merger import MergeError

from . import (
    TEST_API_DOMAIN, TEST_USERNAME, TEST_PASSWORD, TEST_CONFIG_ID,
    SAMPLE_CONFIG_DATA, get_temp_path, cleanup_temp_files
)


class TestGlossaryUpdater:
    """Test cases for GlossaryUpdater class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.updater = GlossaryUpdater(
            domain=TEST_API_DOMAIN,
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
            timeout=30,
            max_retries=3
        )
        cleanup_temp_files()
    
    def teardown_method(self):
        """Clean up after tests."""
        cleanup_temp_files()
    
    def test_init(self):
        """Test GlossaryUpdater initialization."""
        assert self.updater.domain == f"https://{TEST_API_DOMAIN}"
        assert self.updater.username == TEST_USERNAME
        assert self.updater.password == TEST_PASSWORD
        assert self.updater.timeout == 30
        assert self.updater.max_retries == 3
        assert not self.updater._connected
    
    def test_init_with_protocol(self):
        """Test initialization with domain that already has protocol."""
        updater = GlossaryUpdater(
            domain=f"https://{TEST_API_DOMAIN}",
            username=TEST_USERNAME,
            password=TEST_PASSWORD
        )
        assert updater.domain == f"https://{TEST_API_DOMAIN}"
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        with patch.object(self.updater, 'connect') as mock_connect, \
             patch.object(self.updater, 'disconnect') as mock_disconnect:
            
            async with self.updater:
                mock_connect.assert_called_once()
            
            mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connection method."""
        with patch.object(self.updater.api_client, 'connect') as mock_api_connect:
            await self.updater.connect()
            
            mock_api_connect.assert_called_once()
            assert self.updater._connected
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection method."""
        self.updater._connected = True
        
        with patch.object(self.updater.api_client, 'disconnect') as mock_api_disconnect:
            await self.updater.disconnect()
            
            mock_api_disconnect.assert_called_once()
            assert not self.updater._connected
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        with patch.object(self.updater, 'connect') as mock_connect, \
             patch.object(self.updater.api_client, 'test_connection', return_value=True):
            
            result = await self.updater.test_connection()
            
            mock_connect.assert_called_once()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test failed connection test."""
        with patch.object(self.updater, 'connect') as mock_connect, \
             patch.object(self.updater.api_client, 'test_connection', return_value=False):
            
            result = await self.updater.test_connection()
            
            mock_connect.assert_called_once()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_update_from_files_success(self):
        """Test successful update from files."""
        # Create test files
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        # Mock components
        mock_terms = [GlossaryTerm("API", "Application Programming Interface")]
        mock_config = SAMPLE_CONFIG_DATA.copy()
        mock_merge_stats = {
            "strategy": "merge",
            "terms_before": 0,
            "terms_after": 1,
            "terms_added": 1,
            "terms_updated": 0,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        with patch.object(self.updater, 'connect') as mock_connect, \
             patch.object(self.updater.file_processor, 'process_files', return_value=mock_terms), \
             patch.object(self.updater.api_client, 'get_configuration', return_value=mock_config), \
             patch.object(self.updater.merger, 'validate_configuration_structure', return_value=[]), \
             patch.object(self.updater.merger, 'merge_glossary_terms', return_value=(mock_config, mock_merge_stats)), \
             patch.object(self.updater.api_client, 'update_configuration', return_value=mock_config):
            
            result = await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)],
                merge_strategy="merge",
                dry_run=False
            )
            
            assert result["success"] is True
            assert result["config_id"] == TEST_CONFIG_ID
            assert result["files_processed"] == 1
            assert result["terms_extracted"] == 1
            assert result["merge_stats"]["terms_after"] == 1
            assert "updated_configuration" in result
    
    @pytest.mark.asyncio
    async def test_update_from_files_dry_run(self):
        """Test dry run update."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        mock_terms = [GlossaryTerm("API", "Application Programming Interface")]
        mock_config = SAMPLE_CONFIG_DATA.copy()
        mock_merge_stats = {
            "strategy": "merge",
            "terms_before": 0,
            "terms_after": 1,
            "terms_added": 1,
            "terms_updated": 0,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        with patch.object(self.updater, 'connect'), \
             patch.object(self.updater.file_processor, 'process_files', return_value=mock_terms), \
             patch.object(self.updater.api_client, 'get_configuration', return_value=mock_config), \
             patch.object(self.updater.merger, 'validate_configuration_structure', return_value=[]), \
             patch.object(self.updater.merger, 'merge_glossary_terms', return_value=(mock_config, mock_merge_stats)) as mock_merge, \
             patch.object(self.updater.api_client, 'update_configuration') as mock_update:
            
            result = await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)],
                merge_strategy="merge",
                dry_run=True
            )
            
            assert result["success"] is True
            assert result["dry_run"] is True
            assert "updated_configuration" not in result
            mock_update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_from_files_no_files(self):
        """Test update with no files provided."""
        with pytest.raises(GlossaryUpdaterError, match="No file paths or directory paths provided"):
            await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[],
                directory_paths=[]
            )
    
    @pytest.mark.asyncio
    async def test_update_from_files_no_terms(self):
        """Test update when no terms are found."""
        csv_file = get_temp_path("empty.csv")
        csv_file.write_text("phrase,definition\n")  # Empty CSV
        
        with patch.object(self.updater, 'connect'), \
             patch.object(self.updater.file_processor, 'process_files', return_value=[]), \
             pytest.raises(GlossaryUpdaterError, match="No glossary terms found"):
            
            await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)]
            )
    
    @pytest.mark.asyncio
    async def test_update_from_files_authentication_error(self):
        """Test update with authentication error."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        with patch.object(self.updater, 'connect', side_effect=AuthenticationError("Invalid credentials")), \
             pytest.raises(GlossaryUpdaterError, match="Update failed: Invalid credentials"):
            
            await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)]
            )
    
    @pytest.mark.asyncio
    async def test_update_from_files_configuration_error(self):
        """Test update with configuration error."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        mock_terms = [GlossaryTerm("API", "Application Programming Interface")]
        
        with patch.object(self.updater, 'connect'), \
             patch.object(self.updater.file_processor, 'process_files', return_value=mock_terms), \
             patch.object(self.updater.api_client, 'get_configuration', side_effect=ConfigurationError("Config not found")), \
             pytest.raises(GlossaryUpdaterError, match="Update failed: Config not found"):
            
            await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)]
            )
    
    @pytest.mark.asyncio
    async def test_update_from_files_validation_error(self):
        """Test update with configuration validation error."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        mock_terms = [GlossaryTerm("API", "Application Programming Interface")]
        mock_config = SAMPLE_CONFIG_DATA.copy()
        validation_errors = ["Missing required field"]
        
        with patch.object(self.updater, 'connect'), \
             patch.object(self.updater.file_processor, 'process_files', return_value=mock_terms), \
             patch.object(self.updater.api_client, 'get_configuration', return_value=mock_config), \
             patch.object(self.updater.merger, 'validate_configuration_structure', return_value=validation_errors), \
             pytest.raises(GlossaryUpdaterError, match="Configuration validation failed"):
            
            await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)]
            )
    
    @pytest.mark.asyncio
    async def test_get_configuration_info(self):
        """Test getting configuration information."""
        mock_config = SAMPLE_CONFIG_DATA.copy()
        mock_config["analysisEntityList"][0]["resources"] = ["resource-1"]
        
        with patch.object(self.updater, 'connect'), \
             patch.object(self.updater.api_client, 'get_configuration', return_value=mock_config), \
             patch.object(self.updater.merger, '_extract_existing_terms', return_value=[]):
            
            info = await self.updater.get_configuration_info(TEST_CONFIG_ID)
            
            assert info["config_id"] == TEST_CONFIG_ID
            assert info["total_entities"] == 1
            assert info["total_resources"] == 0
            assert info["glossary_entity_exists"] is True
            assert info["current_glossary_terms"] == 0
    
    @pytest.mark.asyncio
    async def test_preview_update(self):
        """Test update preview functionality."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        mock_terms = [GlossaryTerm("API", "Application Programming Interface")]
        mock_config = SAMPLE_CONFIG_DATA.copy()
        mock_preview = {
            "strategy": "merge",
            "terms_current": 0,
            "terms_provided": 1,
            "terms_after": 1,
            "terms_that_would_be_added": [{"phrase": "API", "definition": "Application Programming Interface"}],
            "terms_that_would_be_updated": [],
            "terms_that_would_be_removed": []
        }
        
        with patch.object(self.updater, 'connect'), \
             patch.object(self.updater.file_processor, 'process_files', return_value=mock_terms), \
             patch.object(self.updater.api_client, 'get_configuration', return_value=mock_config), \
             patch.object(self.updater.merger, 'get_merge_preview', return_value=mock_preview):
            
            preview = await self.updater.preview_update(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)],
                merge_strategy="merge"
            )
            
            assert preview["files_to_process"] == 1
            assert preview["terms_extracted"] == 1
            assert preview["terms_after"] == 1
            assert len(preview["terms_that_would_be_added"]) == 1


class TestGlossaryUpdaterIntegration:
    """Integration tests for GlossaryUpdater."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.updater = GlossaryUpdater(
            domain=TEST_API_DOMAIN,
            username=TEST_USERNAME,
            password=TEST_PASSWORD
        )
        cleanup_temp_files()
    
    def teardown_method(self):
        """Clean up after integration tests."""
        cleanup_temp_files()
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        # Create test files
        csv_file = get_temp_path("terms.csv")
        csv_file.write_text("""phrase,definition,category
API,"Application Programming Interface",Technical
REST,"Representational State Transfer",Technical""")
        
        json_file = get_temp_path("terms.json")
        json_file.write_text(json.dumps({
            "glossary": [
                {"phrase": "JSON", "definition": "JavaScript Object Notation"}
            ]
        }))
        
        # Mock all external dependencies
        mock_terms = [
            GlossaryTerm("API", "Application Programming Interface"),
            GlossaryTerm("REST", "Representational State Transfer"),
            GlossaryTerm("JSON", "JavaScript Object Notation")
        ]
        
        mock_config = SAMPLE_CONFIG_DATA.copy()
        mock_updated_config = mock_config.copy()
        mock_merge_stats = {
            "strategy": "merge",
            "terms_before": 0,
            "terms_after": 3,
            "terms_added": 3,
            "terms_updated": 0,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        with patch.object(self.updater.api_client, 'connect'), \
             patch.object(self.updater.file_processor, 'process_files', return_value=mock_terms), \
             patch.object(self.updater.api_client, 'get_configuration', return_value=mock_config), \
             patch.object(self.updater.merger, 'validate_configuration_structure', return_value=[]), \
             patch.object(self.updater.merger, 'merge_glossary_terms', return_value=(mock_updated_config, mock_merge_stats)), \
             patch.object(self.updater.api_client, 'update_configuration', return_value=mock_updated_config), \
             patch.object(self.updater.api_client, 'disconnect'):
            
            async with self.updater:
                result = await self.updater.update_from_files(
                    config_id=TEST_CONFIG_ID,
                    file_paths=[str(csv_file), str(json_file)],
                    merge_strategy="merge"
                )
                
                assert result["success"] is True
                assert result["files_processed"] == 2
                assert result["terms_extracted"] == 3
                assert result["merge_stats"]["terms_after"] == 3
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery scenarios."""
        csv_file = get_temp_path("test.csv")
        csv_file.write_text("phrase,definition\nAPI,Application Programming Interface")
        
        # Test recovery from temporary network error
        mock_terms = [GlossaryTerm("API", "Application Programming Interface")]
        mock_config = SAMPLE_CONFIG_DATA.copy()
        
        call_count = 0
        def mock_get_config(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConfigurationError("Temporary network error")
            return mock_config
        
        with patch.object(self.updater, 'connect'), \
             patch.object(self.updater.file_processor, 'process_files', return_value=mock_terms), \
             patch.object(self.updater.api_client, 'get_configuration', side_effect=mock_get_config), \
             pytest.raises(GlossaryUpdaterError):
            
            await self.updater.update_from_files(
                config_id=TEST_CONFIG_ID,
                file_paths=[str(csv_file)]
            )
            
            # Ensure it attempted the operation
            assert call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])
