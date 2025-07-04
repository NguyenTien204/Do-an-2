from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import logging
from Data_Pipeline.pipelines.extract import JSONPathExtractor, MappingStrategy
from Data_Pipeline.pipelines.extract import SimpleFieldStrategy, NestedObjectStrategy, ArrayStrategy, MappingType, FieldMapping, TableMapping, DataExtractor
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransformationEngine:
    def __init__(self):
        self.extractor = JSONPathExtractor()
        self.strategies = {
            MappingType.SIMPLE: SimpleFieldStrategy(self.extractor),
            MappingType.ONE_TO_ONE: SimpleFieldStrategy(self.extractor),
            MappingType.NESTED_OBJECTS: NestedObjectStrategy(self.extractor),
            MappingType.ARRAYS: ArrayStrategy(self.extractor)
        }
    
    def transform_batch(self, df: pd.DataFrame, config: Dict) -> tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Vectorized transformation approach"""
        main_table_config = self._parse_main_table_config(config)
        related_configs = self._parse_related_configs(config)
        
        # Process main table - vectorized approach
        main_df = self._process_main_table_vectorized(df, main_table_config)
        
        # Process related tables
        related_dfs = {}
        for mapping_type, table_configs in related_configs.items():
            strategy = self.strategies[mapping_type]
            
            for table_config in table_configs:
                table_results = self._process_related_table(df, table_config, strategy, main_df)
                for table_name, data in table_results.items():
                    if table_name not in related_dfs:
                        related_dfs[table_name] = []
                    related_dfs[table_name].extend(data)
        
        # Convert to DataFrames
        for table_name in related_dfs:
            related_dfs[table_name] = pd.DataFrame(related_dfs[table_name])
        
        return main_df, related_dfs
    
    def _process_main_table_vectorized(self, df: pd.DataFrame, config: TableMapping) -> pd.DataFrame:
        result_dict = {}
        
        for field in config.fields:
            if field.source == "_id":
                result_dict[field.target] = df['_id'].astype(str)
            elif '.' in field.source:
                # Handle nested fields
                result_dict[field.target] = df.apply(
                    lambda row: self.extractor.safe_extract(row.to_dict(), field.source), 
                    axis=1
                )
            else:
                result_dict[field.target] = df.get(field.source, field.default_value)
        
        return pd.DataFrame(result_dict)
    
    def _process_related_table(self, df: pd.DataFrame, config: TableMapping, 
                             strategy: MappingStrategy, main_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        all_results = {}
        # Determine the main table primary key name from config
        # Try to get from config.foreign_key (for related table), else default to 'movie_id'
        # But best is to get from main table config
        main_table_pk = None
        if hasattr(main_df, 'columns'):
            # Try to get the first column that ends with '_id', else use the first column
            id_cols = [col for col in main_df.columns if col.endswith('_id')]
            if id_cols:
                main_table_pk = id_cols[0]
            else:
                main_table_pk = main_df.columns[0]
        else:
            main_table_pk = 'movie_id'

        for idx, row in df.iterrows():
            main_id = main_df.iloc[idx].get(main_table_pk)
            row_results = strategy.process(row.to_dict(), config, main_id)

            for table_name, records in row_results.items():
                if table_name not in all_results:
                    all_results[table_name] = []
                all_results[table_name].extend(records)

        return all_results
    
    def _parse_main_table_config(self, config: Dict) -> TableMapping:
        fields = []
        for field_config in config['mappings']['simple_fields']:
            # Map 'type' to 'data_type' for FieldMapping
            field_kwargs = {
                'source': field_config['source'],
                'target': field_config['target'],
                'data_type': field_config.get('type'),
                'default_value': field_config.get('default_value')
            }
            fields.append(FieldMapping(**field_kwargs))
        return TableMapping(table_name=config['main_table'], fields=fields)
    
    def _parse_related_configs(self, config: Dict) -> Dict[MappingType, List[TableMapping]]:
        mappings = config.get("mappings", {})
        related_configs = {}
    
        # Xử lý one_to_one
        if "one_to_one" in mappings:
            one_to_one = []
            for key, val in mappings["one_to_one"].items():
                fields = [
                    FieldMapping(
                        source=f['source'],
                        target=f['target'],
                        data_type=f.get('type'),
                        default_value=f.get('default_value')
                    ) for f in val["fields"]
                ]
                # Lấy foreign_key từ relation nếu có
                foreign_key = None
                if 'relation' in val and 'foreign_key' in val['relation']:
                    foreign_key = val['relation']['foreign_key']
                table = TableMapping(
                    table_name=val.get("table", key),
                    fields=fields,
                    foreign_key=foreign_key,
                    primary_key=val.get("primary_key")
                )
                # Gắn thêm source_path nếu cần (one_to_one thường không cần)
                one_to_one.append(table)
            related_configs[MappingType.ONE_TO_ONE] = one_to_one

        if "nested_objects" in mappings:
            nested = []
            for key, val in mappings["nested_objects"].items():
                # Map 'type' to 'data_type' for each field
                fields = [
                    FieldMapping(
                        source=f['source'],
                        target=f['target'],
                        data_type=f.get('type'),
                        default_value=f.get('default_value')
                    ) for f in val["fields"]
                ]
                # Lấy foreign_key từ relation nếu có
                foreign_key = None
                if 'relation' in val and 'foreign_key' in val['relation']:
                    foreign_key = val['relation']['foreign_key']
                table = TableMapping(
                    table_name=val.get("table_name", key),
                    fields=fields,
                    foreign_key=foreign_key,
                    primary_key=val.get("primary_key")
                )
                # Gắn thêm source_path để extractor dùng
                setattr(table, "source_path", val.get("source_path", key))
                nested.append(table)
            related_configs[MappingType.NESTED_OBJECTS] = nested

        if "arrays" in mappings:
            arrays = []
            for key, val in mappings["arrays"].items():
                # Map 'type' to 'data_type' for each field
                fields = [
                    FieldMapping(
                        source=f['source'],
                        target=f['target'],
                        data_type=f.get('type'),
                        default_value=f.get('default_value')
                    ) for f in val["fields"]
                ]
                table = TableMapping(
                    table_name=val.get("table_name", key),
                    fields=fields,
                    primary_key=val.get("primary_key"),
                )
                # Gắn thêm junction info
                setattr(table, "junction_table", val.get("junction_table"))
                setattr(table, "junction_config", val.get("relation_keys"))
                arrays.append(table)
            related_configs[MappingType.ARRAYS] = arrays

        return related_configs


class ConfigValidator:
    def validate(self, config: Dict) -> None:
        """Validate configuration structure and required fields"""
        required_keys = ['main_table', 'mappings']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")
        
        # Validate mappings structure
        mappings = config['mappings']
        if 'simple_fields' not in mappings:
            raise ValueError("Missing simple_fields in mappings")
        
        # Validate each field mapping
        for field in mappings['simple_fields']:
            if 'source' not in field or 'target' not in field:
                raise ValueError(f"Invalid field mapping: {field}")
