
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Docker Check') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'docker --version'
                    } else {
                        bat 'docker --version'
                    }
                }
            }
        }

        stage('Build VisionPlay Docker Image') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'docker build -t visionplay:latest .'
                    } else {
                        bat 'docker build -t visionplay:latest .'
                    }
                }
            }
        }

        stage('Run VisionPlay Tests') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'docker run --rm --entrypoint python visionplay:latest -m pytest -q'
                    } else {
                        bat 'docker run --rm --entrypoint python visionplay:latest -m pytest -q'
                    }
                }
            }
        }

        stage('Verify Docker Image') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'docker images visionplay'
                    } else {
                        bat 'docker images visionplay'
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'VisionPlay CI pipeline completed successfully!!!!!!'
        }
        failure {
            echo 'Pipeline failed. Check Console Output.'
        }
    }
}
