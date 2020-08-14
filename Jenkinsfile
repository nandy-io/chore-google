pipeline {
    agent any

    stages {
        stage('Build daemon') {
            steps {
                dir('daemon') {
                    sh 'make build'
                }
            }
        }
        stage('Test daemon') {
            steps {
                dir('daemon') {
                    sh 'make test'
                }
            }
        }
        stage('Push daemon') {
            when {
                branch 'master'
            }
            steps {
                dir('daemon') {
                    sh 'make push'
                }
            }
        }
    }
}
