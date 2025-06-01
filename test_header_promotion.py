#!/usr/bin/env python3
"""
Test script for the "Use First Row as Header" functionality
"""

import pandas as pd
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from table_parser_model import TableParserModel
from src.step_history import OperationType

def test_header_promotion():
    """Test the header promotion functionality"""
    print("Testing header promotion functionality...")
    
    # Create a model instance
    model = TableParserModel()
    
    # Create a test dataframe with generic column names
    test_data = {
        0: ['Name', 'John', 'Jane', 'Bob'],
        1: ['Age', '25', '30', '35'],
        2: ['City', 'New York', 'London', 'Paris']
    }
    test_df = pd.DataFrame(test_data)
    
    print("Original DataFrame:")
    print(test_df)
    print()
    
    # Add the test dataframe to the model
    table_id = 0
    model.tables = [{"id": table_id, "name": "Test Table", "type": "standard"}]
    model.table_dataframes[table_id] = test_df
    
    # Test the header promotion
    success, message = model.promote_first_row_to_header(table_id)
    
    print(f"Promotion result: {success}")
    print(f"Message: {message}")
    print()
    
    if success:
        # Get the modified dataframe
        modified_df = model.get_table_preview(table_id)
        print("Modified DataFrame:")
        print(modified_df)
        print()
        
        # Check if the operation was recorded in history
        steps = model.get_steps()
        header_promotion_steps = [step for step in steps if step.operation == OperationType.PROMOTE_HEADER]
        
        print(f"Number of header promotion steps recorded: {len(header_promotion_steps)}")
        if header_promotion_steps:
            step = header_promotion_steps[0]
            print(f"Step details: {step.details}")
            print(f"Step metadata: {step.metadata}")
        
        # Verify the headers are correct
        expected_headers = ['Name', 'Age', 'City']
        actual_headers = list(modified_df.columns)
        
        print(f"Expected headers: {expected_headers}")
        print(f"Actual headers: {actual_headers}")
        
        if actual_headers == expected_headers:
            print("✅ Headers match expected values!")
        else:
            print("❌ Headers do not match expected values!")
        
        # Verify the data is correct
        expected_first_row = ['John', '25', 'New York']
        actual_first_row = list(modified_df.iloc[0])
        
        print(f"Expected first row: {expected_first_row}")
        print(f"Actual first row: {actual_first_row}")
        
        if actual_first_row == expected_first_row:
            print("✅ First row data matches expected values!")
        else:
            print("❌ First row data does not match expected values!")
    
    # Test edge cases
    print("\n" + "="*50)
    print("Testing edge cases...")
    
    # Test with empty dataframe
    empty_df = pd.DataFrame()
    model.table_dataframes[1] = empty_df
    model.tables.append({"id": 1, "name": "Empty Table", "type": "standard"})
    
    success, message = model.promote_first_row_to_header(1)
    print(f"Empty table test - Success: {success}, Message: {message}")
    
    # Test with single row dataframe
    single_row_df = pd.DataFrame({0: ['Header1'], 1: ['Header2']})
    model.table_dataframes[2] = single_row_df
    model.tables.append({"id": 2, "name": "Single Row Table", "type": "standard"})
    
    success, message = model.promote_first_row_to_header(2)
    print(f"Single row table test - Success: {success}, Message: {message}")
    
    # Test with non-existent table
    success, message = model.promote_first_row_to_header(999)
    print(f"Non-existent table test - Success: {success}, Message: {message}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_header_promotion() 