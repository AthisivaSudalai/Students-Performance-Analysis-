import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import os

class DataProcessor:
    def __init__(self, filepath):
        self.filepath = filepath
        self.df = None
        self.required_columns = ['Name', 'Test1', 'Test2', 'Test3']
        
    def validate_file(self):
        """Validate the uploaded file format"""
        try:
            # Load file based on extension
            if self.filepath.endswith('.csv'):
                df = pd.read_csv(self.filepath)
            elif self.filepath.endswith('.xlsx'):
                df = pd.read_excel(self.filepath)
            else:
                return {'valid': False, 'error': 'Unsupported file format'}
            
            # Enforce exactly 4 columns
            if len(df.columns) != 4:
                return {'valid': False, 'error': f'File must have exactly 4 columns (Name, Test1, Test2, Test3). Found {len(df.columns)}: {", ".join(df.columns)}'}

            # Check required columns
            missing_cols = [col for col in self.required_columns if col not in df.columns]
            if missing_cols:
                return {'valid': False, 'error': f'Missing columns: {", ".join(missing_cols)}'}
            
            # Check data types for test columns
            for col in ['Test1', 'Test2', 'Test3']:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    return {'valid': False, 'error': f'Column {col} must contain numeric values'}
            
            # Check for missing values
            if df[self.required_columns].isnull().any().any():
                return {'valid': False, 'error': 'File contains missing values'}
            
            # Check marks range (0-50)
            for col in ['Test1', 'Test2', 'Test3']:
                if (df[col] < 0).any() or (df[col] > 50).any():
                    return {'valid': False, 'error': f'Marks in {col} must be between 0 and 50'}
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def load_data(self):
        """Load the validated data"""
        if self.filepath.endswith('.csv'):
            self.df = pd.read_csv(self.filepath)
        elif self.filepath.endswith('.xlsx'):
            self.df = pd.read_excel(self.filepath)
        
        # Calculate additional columns
        self.df['Total'] = self.df['Test1'] + self.df['Test2'] + self.df['Test3']
        self.df['Average'] = self.df['Total'] / 3
        self.df['Rank'] = self.df['Total'].rank(ascending=False, method='min').astype(int)
        
        # Pass/Fail categorization (pass mark = 20 out of 50)
        self.df['Status'] = self.df['Average'].apply(lambda x: 'Pass' if x >= 20 else 'Fail')
        
    def analyze_data(self):
        """Perform comprehensive analysis"""
        analysis = {}

        def to_py(val):
            """Convert numpy scalar to native Python type for JSON serialisation."""
            if hasattr(val, 'item'):
                return val.item()
            return val

        # Individual test analysis
        for test in ['Test1', 'Test2', 'Test3']:
            analysis[test] = {
                'average':          round(to_py(self.df[test].mean()), 2),
                'highest':          round(to_py(self.df[test].max()),  2),
                'lowest':           round(to_py(self.df[test].min()),  2),
                'pass_percentage':  round(to_py((self.df[test] >= 20).sum() / len(self.df) * 100), 2)
            }

        # Cumulative analysis
        analysis['cumulative'] = {
            'total_students':           int(len(self.df)),
            'overall_average':          round(to_py(self.df['Average'].mean()), 2),
            'overall_pass_percentage':  round(to_py((self.df['Status'] == 'Pass').sum() / len(self.df) * 100), 2),
            'overall_fail_percentage':  round(to_py((self.df['Status'] == 'Fail').sum() / len(self.df) * 100), 2)
        }

        # Top performers (top 5) — convert every value to a native Python type
        top_students = self.df.nlargest(5, 'Total')[['Name', 'Test1', 'Test2', 'Test3', 'Total', 'Average', 'Rank']]
        analysis['top_performers'] = [
            {k: (v.item() if hasattr(v, 'item') else v) for k, v in row.items()}
            for row in top_students.to_dict('records')
        ]

        # Bottom performers (bottom 5)
        bottom_students = self.df.nsmallest(5, 'Total')[['Name', 'Test1', 'Test2', 'Test3', 'Total', 'Average', 'Rank']]
        analysis['bottom_performers'] = [
            {k: (v.item() if hasattr(v, 'item') else v) for k, v in row.items()}
            for row in bottom_students.to_dict('records')
        ]

        # Best-2 average: average of the 2 highest marks out of 3 tests per student
        self.df['Best2Avg'] = self.df[['Test1', 'Test2', 'Test3']].apply(
            lambda r: round(sum(sorted(r, reverse=True)[:2]) / 2, 2), axis=1
        )
        best2_cols = ['Name', 'Test1', 'Test2', 'Test3', 'Best2Avg']

        top_best2 = self.df.nlargest(5, 'Best2Avg')[best2_cols]
        analysis['top_best2'] = [
            {k: (round(v.item(), 2) if hasattr(v, 'item') else v) for k, v in row.items()}
            for row in top_best2.to_dict('records')
        ]

        bottom_best2 = self.df.nsmallest(5, 'Best2Avg')[best2_cols]
        analysis['bottom_best2'] = [
            {k: (round(v.item(), 2) if hasattr(v, 'item') else v) for k, v in row.items()}
            for row in bottom_best2.to_dict('records')
        ]

        # Student progress tracking
        self.df['Progress'] = self.df['Test3'] - self.df['Test1']
        analysis['progress'] = {
            'improving_count': int((self.df['Progress'] > 0).sum()),
            'declining_count': int((self.df['Progress'] < 0).sum()),
            'stable_count':    int((self.df['Progress'] == 0).sum())
        }

        return analysis
    
    def generate_visualizations(self):
        """Generate all required charts"""
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (10, 6)
        
        # Clear any existing plots
        plt.close('all')
        
        # 1. Histogram - Marks distribution for each test
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        for idx, test in enumerate(['Test1', 'Test2', 'Test3']):
            axes[idx].hist(self.df[test], bins=10, color='skyblue', edgecolor='black')
            axes[idx].set_title(f'{test} Distribution')
            axes[idx].set_xlabel('Marks')
            axes[idx].set_ylabel('Frequency')
        plt.tight_layout()
        plt.savefig('static/charts/histogram.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # 2. Bar chart - Average marks per test
        plt.figure(figsize=(10, 6))
        averages = [self.df['Test1'].mean(), self.df['Test2'].mean(), self.df['Test3'].mean()]
        tests = ['Test 1', 'Test 2', 'Test 3']
        bars = plt.bar(tests, averages, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        plt.title('Average Marks per Test', fontsize=16, fontweight='bold')
        plt.xlabel('Test', fontsize=12)
        plt.ylabel('Average Marks', fontsize=12)
        plt.ylim(0, 50)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}',
                    ha='center', va='bottom', fontsize=10)
        
        plt.savefig('static/charts/bar_chart.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # 3. Line chart - Student progress (top 10 students)
        plt.figure(figsize=(12, 6))
        top_10 = self.df.nlargest(10, 'Total')
        for idx, row in top_10.iterrows():
            plt.plot(['Test 1', 'Test 2', 'Test 3'], 
                    [row['Test1'], row['Test2'], row['Test3']], 
                    marker='o', label=row['Name'])
        plt.title('Student Progress (Top 10)', fontsize=16, fontweight='bold')
        plt.xlabel('Test', fontsize=12)
        plt.ylabel('Marks', fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('static/charts/line_chart.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # 4. Pie chart - Pass vs Fail
        plt.figure(figsize=(8, 8))
        status_counts = self.df['Status'].value_counts()
        n = len(status_counts)
        colors = ['#2ECC71', '#E74C3C'][:n]
        explode = [0.05] * n
        plt.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%',
                colors=colors, explode=explode, shadow=True, startangle=90)
        plt.title('Pass vs Fail Distribution', fontsize=16, fontweight='bold')
        plt.savefig('static/charts/pie_chart.png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # 5. Bar chart - Top/Bottom performers
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Top 5 performers
        top_5 = self.df.nlargest(5, 'Total')
        ax1.barh(top_5['Name'], top_5['Total'], color='#2ECC71')
        ax1.set_title('Top 5 Performers', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Total Marks', fontsize=12)
        ax1.invert_yaxis()
        
        # Bottom 5 performers
        bottom_5 = self.df.nsmallest(5, 'Total')
        ax2.barh(bottom_5['Name'], bottom_5['Total'], color='#E74C3C')
        ax2.set_title('Bottom 5 Performers', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Total Marks', fontsize=12)
        ax2.invert_yaxis()
        
        plt.tight_layout()
        plt.savefig('static/charts/performers.png', dpi=100, bbox_inches='tight')
        plt.close()
