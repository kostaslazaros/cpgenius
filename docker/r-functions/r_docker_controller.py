# r_docker_controller.py
import json

import docker


class RDockerController:
    def __init__(self, image_name="konlaz/r-analysis"):
        self.client = docker.from_env()
        self.client.ping()
        self.image_name = image_name

    def run_dmp_analysis(
        self,
        csv_path: str,
        output_dir: str,
        condition1: str,
        condition2: str,
        delta_beta: float = 0.4,
        p_value: float = 0.05,
    ):
        """Run DMP analysis using the dmp_analysis.R script"""

        volumes = {
            str(csv_path): {"bind": "/input", "mode": "ro"},
            str(output_dir): {"bind": "/output", "mode": "rw"},
        }

        # Prepare command
        cmd = [
            "dmp_volcano.R",
            "--condition1",
            condition1,
            "--condition2",
            condition2,
            "--delta_beta",
            str(delta_beta),
            "--p_value",
            str(p_value),
        ]

        try:
            print("Starting container...")
            print(f"Using image: {self.image_name}")
            print(f"Command: {cmd}")
            print(f"Volumes: {volumes}")
            # Run the container
            container = self.client.containers.run(
                self.image_name, command=cmd, volumes=volumes, detach=True, remove=True
            )

            # Wait for completion and get logs
            result = container.wait()
            logs = container.logs().decode("utf-8")
            print(f"Container finished with exit code: {result['StatusCode']}")
            # Parse the JSON output
            output = json.loads(logs)

            # Add output directory to result
            output["output_dir"] = output_dir

            return output

        except docker.errors.ContainerError as e:
            return {"status": "error", "message": str(e), "exit_code": e.exit_status}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_idat_preprocessor(
        self,
        idat_dir: str,
        output_dir: str,
    ):
        """Run IDAT processing using the idat_processing.R script"""

        volumes = {
            str(idat_dir): {"bind": "/input", "mode": "ro"},
            str(output_dir): {"bind": "/output", "mode": "rw"},
        }

        # Prepare command
        cmd = [
            "idat_preprocessor.R",
        ]

        try:
            # Run the container
            print("Starting container...")
            print(f"Using image: {self.image_name}")
            print(f"Command: {cmd}")
            print(f"Volumes: {volumes}")

            container = self.client.containers.run(
                self.image_name,
                remove=True,
                detach=True,  # Run in background so we can monitor
                command=cmd,
                volumes=volumes,
            )

            result = container.wait()
            logs = container.logs().decode("utf-8")

            print(f"Container finished with exit code: {result['StatusCode']}")
            print(f"Logs: {logs}")

            # Parse the JSON output
            if logs.strip():
                try:
                    # Try to find JSON in the logs (it might be mixed with other output)
                    lines = logs.strip().split("\n")
                    json_line = None
                    for line in reversed(
                        lines
                    ):  # Check from end, JSON usually comes last
                        line = line.strip()
                        if line.startswith("{") and line.endswith("}"):
                            json_line = line
                            break

                    if json_line:
                        output = json.loads(json_line)
                    else:
                        # No JSON found, but execution was successful
                        output = {
                            "status": "success",
                            "message": "R script executed successfully",
                            "raw_logs": logs,
                        }
                except json.JSONDecodeError:
                    output = {
                        "status": "success",
                        "message": "R script executed successfully but no valid JSON output",
                        "raw_logs": logs,
                    }
            else:
                output = {"status": "error", "message": "No output from container"}

            # Add output directory to result
            output["output_dir"] = output_dir

            return output

        except docker.errors.ContainerError as e:
            return {"status": "error", "message": str(e), "exit_code": e.exit_status}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Example usage
def test_idat_preprocessor():
    import os

    # Initialize controller
    print("running IDAT preprocessor...")
    controller = RDockerController()

    # Use absolute paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    idat_dir = os.path.join(current_dir, "idat4")
    output_dir = os.path.join(current_dir, "out1")

    print(f"Input directory: {idat_dir}")
    print(f"Output directory: {output_dir}")

    controller.run_idat_preprocessor(idat_dir=idat_dir, output_dir=output_dir)


def test_dmp_volcano():
    import os

    print("running dmp volcano...")
    controller = RDockerController()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = current_dir
    output_dir = os.path.join(current_dir, "out2")

    print(f"Input directory: {csv_path}")
    print(f"Output directory: {output_dir}")

    controller.run_dmp_analysis(
        csv_path=csv_path,
        output_dir=output_dir,
        condition1="AVPC",
        condition2="Indolent",
    )


if __name__ == "__main__":
    test_dmp_volcano()
    test_idat_preprocessor()
