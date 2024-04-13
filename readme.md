
# GitLab Archiver

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- pip
- pipenv (or you can just use pip like a nerd)

### Installation and running

#### Using pipenv (recommended)

```shell
# 1. Clone the repository
git clone https://github.com/ashleylamont/gitlab-archiver.git
# 2. Change into the project directory
cd gitlab-archiver
# 3. (Optional) Install pipenv
pip install --user pipenv
# 4. Install the project dependencies
pipenv install
# 5. Configure .env file
cp .env.example .env
nano .env # (or your editor of choice)
# 6. Run the project
pipenv run start
```

#### Using pip (not recommended)

```shell
# 1. Clone the repository
git clone https://github.com/ashleylamont/gitlab-archiver.git
# 2. Change into the project directory
cd gitlab-archiver
# 3. Install the project dependencies
pip install -r requirements.txt
# 4. Configure .env file
cp .env.example .env
nano .env # (or your editor of choice)
# 5. Run the project
python main.py
```

## GitLab API Token

To use the GitLab API, you need to generate a personal access token. Follow these steps:

1. Log in to GitLab.
2. Click on your avatar in the top right and select "Settings".
3. In the left sidebar, click on "Access Tokens".
4. Choose a name and optional expiry date for the token.
5. Choose the desired scopes (you'll probably want "api").
6. Click "Create personal access token".
7. Save the personal access token somewhere safe. Once you leave or refresh the page, you won't be able to access it again.

## .env File

Create a `.env` file in the root of your project and add your GitLab API token like so:

```
GITLAB_API_TOKEN=your_token_here
GITLAB_URL=https://gitlab.cecs.anu.edu.au
```

Replace `your_token_here` with the token you generated earlier.

You can also replace `https://gitlab.cecs.anu.edu.au` with the URL of your GitLab instance.

## Contributing

Contributions are welcome! Please raise an issue or submit a pull request.

## License

This project is licensed under the GNU GPLv3 License - see the `LICENSE.md` file for details
