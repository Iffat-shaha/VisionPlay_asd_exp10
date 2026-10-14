

pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out VisionPlay'
                checkout scm
            }
        }

        stage('Docker Check') {
            steps {
                echo 'Checking Docker connection'

                script {
                    if (isUnix()) {
                        sh 'docker --version'
                    } else {
                        bat 'docker --version'
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!!!!'
        }

        failure {
            echo 'Pipeline failed. Check Console Output'
        }
    }
}

