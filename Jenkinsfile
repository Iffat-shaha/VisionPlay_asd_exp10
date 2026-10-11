
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

        stage('Python Syntax Check') {
            steps {
                bat 'python -m py_compile "game final.py"'
            }
        }
    }

    post {
        success {
            echo 'VisionPlay CI pipeline completed successfully - polling test.'
        }
        failure {
            echo 'VisionPlay CI pipeline failed. Check the console output.'
        }
    }
}
