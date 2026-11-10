# Automatic Task Scaling Final Project
Created by Andrew, Dixon, Eli, Noah, and Will

## What is it?

This is our final project for the BYU CYBER 344 class. It's a full stack application that uses multiple levels of virtualization to do the following:
1. A user logs onto our website, enters a url, and selects a given task.
2. The system will take the task and url, and spin up a docker container with a python worker for the task.
3. The user can submit as many tasks as quickly as they'd like, and Kubernetes will automatically scale as the demand increases.
4. If a task fails, the user will recieve a simple message explaining why

## What kinda security?

The website is designed to take any form of user input, and our application safely parses the data, prevents the data from doing anything it shouldn't, and moves the data along to a container which limits overarching access to the system. Additionally, base users can only see tasks that they have requested. Administrative users have the ability to see all of the tasks from every user, and the underlying logs of the app.