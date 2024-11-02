class PRAnalysisConfig:
    def __init__(self, file_path):
        self.file_path = file_path
        self.properties = {}

    def read_properties(self):
        try:
            with open(self.file_path, 'r') as file:
                for line in file:
                    # Skip empty lines and comments
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Split the line into key and value using '='
                        key, value = line.split('=', 1)
                        # Store in dictionary after removing leading/trailing spaces
                        self.properties[key.strip()] = value.strip()
        except FileNotFoundError:
            print(f"Error: File {self.file_path} not found")
            self.properties = {}
        except Exception as e:
            print(f"Error reading properties file: {str(e)}")
            self.properties = {}

        return self.properties

# Example usage:
if __name__ == "__main__":
    # Create an instance of PRAnalysisConfig
    pr_analysis_config = PRAnalysisConfig('pr_analysis.properties')
    
    # Read the properties
    properties_dict = pr_analysis_config.read_properties()
    
    # Print the resulting dictionary
    if properties_dict:
        print("Properties Dictionary:")
        for key, value in properties_dict.items():
            print(f"{key}: {value}")

