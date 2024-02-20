import subprocess
from concurrent.futures import ThreadPoolExecutor
import yaml
import tempfile
import os
import argparse

def execute_command(command):
    try:
        # Execute the command and capture its output
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        return command, output
    except subprocess.CalledProcessError as e:
        # Capture error output if the command fails
        return command, e.output

def main():
    parser = argparse.ArgumentParser(description="LlamaCpp Multimodel Deploy utility")
    parser.add_argument("--deploy", action="store_true", help="Deploy model stacks")
    parser.add_argument("--destroy", action="store_true", help="Destroy model stacks")
    parser.add_argument("--config",help="Multimodel config file", default="multimodel_config.yaml" )
    parser.add_argument("--output-dir", help="Output directory for model deployment assets", default="./cdk.out/.multimodel_deploy")
    args = parser.parse_args()

    # list of cdk stacks
    dotfiles_dir = args.output_dir
    with open(args.config, 'r') as f:
        project_config = yaml.safe_load(f)

        os.makedirs(dotfiles_dir, exist_ok=True)

        dotfiles = []
        for idx, project in enumerate(project_config['project']):
            dotfile = tempfile.NamedTemporaryFile(prefix='.', suffix='.yaml', delete=False, dir=dotfiles_dir)
            dotfiles.append(dotfile.name)
            with open(dotfile.name, 'w') as f:
                yaml.dump({'project': project}, f)

    # List of commands to execute
    commands = []
    print('Running following in parallel : ')
    for idx, config_file in enumerate(dotfiles):
        output_dir_name = os.path.splitext(config_file)[0]
        if args.deploy:
            commands.append(f"cdk deploy --context config_file='{config_file}' --output='{output_dir_name}' --require-approval=never")
        elif args.destroy:
            commands.append(f"cdk destroy --context config_file='{config_file}' --output='{output_dir_name}' --require-approval=never --force")
        else:
            parser.print_help()
        print(commands[idx])
    
    
    # Maximum number of threads to use
    max_threads = 5

    # Execute commands in parallel using a ThreadPoolExecutor
    with ThreadPoolExecutor(max_threads) as executor:
        # Submit each command to the executor
        futures = [executor.submit(execute_command, cmd) for cmd in commands]
    
        # Wait for all commands to complete and collect results
        for future in futures:
            command, result = future.result()
            print(f"Output of command '{command}':")
            print(result)
            print("=" * 50)

if __name__ == "__main__":
    main()