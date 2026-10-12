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

        // ADD THE BUILD STAGE HERE
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
    }
}
