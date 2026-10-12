
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'VisionPlay source code is ready.'
            }
        }

        stage('Environment Check') {
            steps {
                bat 'python --version'
                bat 'git --version'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Python Syntax Check') {
            steps {
                bat 'python -m py_compile "game final.py"'
            }
        }

        stage('Automated Tests') {
            steps {
                bat 'python -m pytest -v'
            }
        }
    }
    stage('Docker Connection and Image Check') {
    steps {
        bat 'docker --version'
        bat 'docker info'
        bat 'docker pull shravanip20/visionplay:latest'
        bat 'docker image inspect shravanip20/visionplay:latest'
    }
}

    post {
        success {
            echo 'VisionPlay CI pipeline completed successfully - all checks passed.'
        }
        failure {
            echo 'VisionPlay CI pipeline failed. Check the console output.'
        }
    }
}
