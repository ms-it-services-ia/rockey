package com.rockey;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class RockeyGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(RockeyGatewayApplication.class, args);
    }
}
