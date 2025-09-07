## Setup Instructions

Build the Docker image:

```bash
docker build -t konlaz/r-analysis .
```

Organize your data:

Place IDAT files in a directory (e.g., ./idat_data)

Ensure you have a SampleSheet.csv in the IDAT directory

Run the analysis:

```bash
uv run  r_docker_controller.py
```
