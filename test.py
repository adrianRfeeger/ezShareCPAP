import subprocess

def get_interface_name():
    command = 'networksetup -listallhardwareports'
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if 'Wi-Fi' in line or 'Wi-Fi' in line.lower():  # Ensuring case insensitivity
                next_line = lines[i + 1].strip()
                if next_line.startswith('Device:'):
                    return next_line.split(':')[1].strip()
    except subprocess.CalledProcessError as e:
        print(f"Failed to run command: {e}")
    return None

interface_name = get_interface_name()
print(f"Interface Name: {interface_name}")
